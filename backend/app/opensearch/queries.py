"""Request bodies for `_search`. Pure functions: filters in, dictionaries out, no I/O."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.opensearch.documents import severity_filter
from app.schemas.filters import (
    AlertFilterParams,
    AlertListParams,
    AlertSort,
    RequestField,
    RequestValueParams,
    SortOrder,
    TimeFrame,
    csv,
)

# index.max_result_window: from + size may not exceed it.
MAX_RESULT_WINDOW = 10_000
COMPOSITE_PAGE_SIZE = 1_000

TIMESTAMP = "@timestamp"
SOURCE_IP = "source.ip"
TARGET_IP = "destination.ip"
RULE_NAME = "rule.name"
SENSOR = "observer.name"
# On an alert: the key of its request document (request_line.py).
REQUEST_KEY = "snort.request_key"

# Fields of the request documents.
REQUEST_FIELDS = {
    RequestField.USER_AGENT: "user_agent.original",
    RequestField.HOST: "url.domain",
    RequestField.CLIENT_IP: "network.forwarded_ip",
}

# A filter on request headers selects request documents, and the alerts follow by key. More keys than
# this are refused, because the key list travels in the alert query (index.max_terms_count is 65,536).
MAX_REQUEST_KEYS = MAX_RESULT_WINDOW - 1
# A request document is stamped when the sensor wrote it, never before its alert. A little slack covers
# clock differences, and the days after the range cover an agent that catches up after an outage.
REQUEST_CLOCK_SLACK = timedelta(minutes=5)
REQUEST_CATCH_UP = timedelta(days=1)

_SORT_FIELDS = {
    AlertSort.DETECT_TIME: TIMESTAMP,
    AlertSort.SEVERITY: "event.severity",
    AlertSort.CLASSIFICATION: RULE_NAME,
    AlertSort.SOURCE_IP: SOURCE_IP,
    AlertSort.TARGET_IP: TARGET_IP,
    AlertSort.ANALYZER: SENSOR,
}

# Days and weeks are calendar units, so a day is 23 or 25 hours long where the zone changes its
# clocks. Everything shorter is a fixed length.
_CALENDAR = {TimeFrame.DAY, TimeFrame.WEEK}


@dataclass(frozen=True)
class RequestKeys:
    """Keys of the request documents that the header filters select, resolved by the repository."""

    include: list[str] | None = None  # None: no filter on what the request had
    exclude: list[str] = field(default_factory=list)


def filter_clauses(
    filters: AlertFilterParams, keys: RequestKeys | None = None
) -> list[dict[str, Any]]:
    """The `bool.filter` list: every condition is exact, so none of them needs scoring."""
    clauses: list[dict[str, Any]] = []
    bounds = {
        key: value.isoformat()
        for key, value in (("gte", filters.start_date), ("lte", filters.end_date))
        if value
    }
    if bounds:
        clauses.append({"range": {TIMESTAMP: bounds}})
    if filters.severity:
        clauses.append(severity_filter(csv(filters.severity)))
    if filters.classification:
        clauses.append({"terms": {RULE_NAME: csv(filters.classification)}})
    if filters.server:
        clauses.append({"terms": {SENSOR: csv(filters.server)}})
    # A term query on an ip field accepts a CIDR network as its value.
    if filters.source_ip:
        clauses.append({"term": {SOURCE_IP: filters.source_ip}})
    if filters.target_ip:
        clauses.append({"term": {TARGET_IP: filters.target_ip}})
    if filters.require_ips:
        clauses.append({"exists": {"field": SOURCE_IP}})
        clauses.append({"exists": {"field": TARGET_IP}})
    if keys is not None:
        # An empty include list selects nothing, which is right: no request matched.
        if keys.include is not None:
            clauses.append({"terms": {REQUEST_KEY: keys.include}})
        # Alerts without a request (every other protocol) stay: they are not in the list.
        if keys.exclude:
            clauses.append(
                {"bool": {"must_not": [{"terms": {REQUEST_KEY: keys.exclude}}]}}
            )
    return clauses


def _query(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    return {"bool": {"filter": clauses}}


def list_body(
    params: AlertListParams, keys: RequestKeys | None = None
) -> dict[str, Any]:
    order = params.sort_order.value
    # Severity is a Snort priority where 1 is the most severe, so "most severe first"
    # (desc) sorts the number ascending.
    if params.sort_by is AlertSort.SEVERITY:
        order = "asc" if params.sort_order is SortOrder.DESC else "desc"
    return {
        "query": _query(filter_clauses(params, keys)),
        # event.id makes the order total, so pages neither overlap nor skip.
        "sort": [{_SORT_FIELDS[params.sort_by]: {"order": order}}, {"event.id": "asc"}],
        "from": params.offset,
        "size": params.size,
        "track_total_hits": True,
        # The list shows neither the raw line nor the payload, the two largest fields.
        "_source": {"excludes": ["event.original", "snort.b64_data"]},
    }


def _composite(
    query: dict[str, Any] | None, fields: list[str], with_latest: bool
) -> dict[str, Any]:
    """
    A composite aggregation named `rows`. Unlike `terms`, it can be paged to the end, so
    the result is complete however many distinct values exist.
    """
    rows: dict[str, Any] = {
        "composite": {
            "size": COMPOSITE_PAGE_SIZE,
            "sources": [{field: {"terms": {"field": field}}} for field in fields],
        }
    }
    if with_latest:
        rows["aggs"] = {"latest": {"max": {"field": TIMESTAMP}}}
    body: dict[str, Any] = {"size": 0, "aggs": {"rows": rows}}
    if query:
        body["query"] = query
    return body


def pairs_body(
    filters: AlertFilterParams, keys: RequestKeys | None = None
) -> dict[str, Any]:
    return _composite(
        _query(filter_clauses(filters, keys)), [SOURCE_IP, TARGET_IP], with_latest=True
    )


def pair_rules_body(
    filters: AlertFilterParams,
    pairs: list[tuple[str, str]],
    keys: RequestKeys | None = None,
) -> dict[str, Any]:
    """Rule names per pair, limited to the given pairs (one page of the pair list)."""
    on_page = {
        "bool": {
            "should": [
                {
                    "bool": {
                        "filter": [{"term": {SOURCE_IP: s}}, {"term": {TARGET_IP: t}}]
                    }
                }
                for s, t in pairs
            ],
            "minimum_should_match": 1,
        }
    }
    return _composite(
        _query([*filter_clauses(filters, keys), on_page]),
        [SOURCE_IP, TARGET_IP, RULE_NAME],
        with_latest=True,
    )


def distinct_body(field: str) -> dict[str, Any]:
    return _composite(None, [field], with_latest=False)


def timeline_body(
    filters: AlertFilterParams,
    time_frame: TimeFrame,
    time_zone: str = "UTC",
    keys: RequestKeys | None = None,
) -> dict[str, Any]:
    histogram: dict[str, Any] = {
        "field": TIMESTAMP,
        (
            "calendar_interval" if time_frame in _CALENDAR else "fixed_interval"
        ): time_frame.value,
        "time_zone": time_zone,
        # Empty buckets stay in, so the chart is a continuous series and
        # averages over it count the quiet hours. The range query above
        # already limits the documents; extended_bounds only adds the empty
        # buckets before the first and after the last alert.
        "min_doc_count": 0,
    }
    if filters.start_date and filters.end_date:
        histogram["extended_bounds"] = {
            "min": filters.start_date.isoformat(),
            "max": filters.end_date.isoformat(),
        }
    return {
        "size": 0,
        "query": _query(filter_clauses(filters, keys)),
        "aggs": {"rows": {"date_histogram": histogram}},
    }


def request_body(companion_id: str) -> dict[str, Any]:
    return {
        "query": {"ids": {"values": [companion_id]}},
        "size": 1,
        "_source": [
            "snort.http_request",
            "snort.xff",
            "user_agent.original",
            "url.domain",
            "network.forwarded_ip",
        ],
    }


def _request_time_range(
    start: datetime | None, end: datetime | None
) -> list[dict[str, Any]]:
    bounds: dict[str, str] = {}
    if start:
        bounds["gte"] = (start - REQUEST_CLOCK_SLACK).isoformat()
    if end:
        bounds["lte"] = (end + REQUEST_CATCH_UP).isoformat()
    return [{"range": {TIMESTAMP: bounds}}] if bounds else []


def _any_of(field_name: str, values: list[str]) -> dict[str, Any]:
    if field_name == REQUEST_FIELDS[RequestField.CLIENT_IP]:
        # A term query on an ip field accepts a CIDR network as its value.
        terms = [{"term": {field_name: value}} for value in values]
        return {"bool": {"should": terms, "minimum_should_match": 1}}
    return {"terms": {field_name: values}}


def request_keys_body(
    filters: AlertFilterParams, exclude: bool
) -> dict[str, Any] | None:
    """
    The request documents that carry the keys. Include values all have to hold (the request has one of
    the user agents and one of the hosts), exclude values hide a request that matches any of them.
    None when the filter holds no value of that kind.
    """
    values = (
        (
            REQUEST_FIELDS[RequestField.USER_AGENT],
            filters.exclude_user_agent if exclude else filters.user_agent,
        ),
        (
            REQUEST_FIELDS[RequestField.HOST],
            filters.exclude_host if exclude else filters.host,
        ),
        (
            REQUEST_FIELDS[RequestField.CLIENT_IP],
            filters.exclude_client_ip if exclude else filters.client_ip,
        ),
    )
    conditions = [_any_of(name, found) for name, found in values if found]
    if not conditions:
        return None
    query: dict[str, Any] = {
        "filter": _request_time_range(filters.start_date, filters.end_date)
    }
    if exclude:
        query |= {"should": conditions, "minimum_should_match": 1}
    else:
        query["filter"] += conditions
    return {
        "query": {"bool": query},
        "size": MAX_RESULT_WINDOW,
        "_source": False,
        "sort": [{"_doc": "asc"}],
    }


def _wildcard_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("*", "\\*").replace("?", "\\?")


def request_values_body(params: RequestValueParams) -> dict[str, Any]:
    """The most common values of one header in the range, for the filter's suggestions."""
    name = REQUEST_FIELDS[params.field]
    query: dict[str, Any] = {
        "bool": {"filter": _request_time_range(params.start_date, params.end_date)}
    }
    # Wildcards do not exist on an ip field; the repository narrows those by text.
    if params.q and params.field is not RequestField.CLIENT_IP:
        query["bool"]["filter"].append(
            {
                "wildcard": {
                    name: {
                        "value": f"*{_wildcard_escape(params.q)}*",
                        "case_insensitive": True,
                    }
                }
            }
        )
    return {
        "size": 0,
        "query": query,
        "aggs": {"rows": {"terms": {"field": name, "size": params.size}}},
    }
