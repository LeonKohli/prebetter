"""Request bodies for `_search`. Pure functions: filters in, dictionaries out, no I/O."""

from typing import Any

from app.opensearch.documents import severity_filter
from app.schemas.filters import (
    AlertFilterParams,
    AlertListParams,
    AlertSort,
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

_SORT_FIELDS = {
    AlertSort.DETECT_TIME: TIMESTAMP,
    AlertSort.SEVERITY: "event.severity",
    AlertSort.CLASSIFICATION: RULE_NAME,
    AlertSort.SOURCE_IP: SOURCE_IP,
    AlertSort.TARGET_IP: TARGET_IP,
    AlertSort.ANALYZER: SENSOR,
}

_INTERVALS = {
    TimeFrame.MINUTE: "1m",
    TimeFrame.HOUR: "1h",
    TimeFrame.DAY: "1d",
    TimeFrame.WEEK: "1w",
}


def filter_clauses(filters: AlertFilterParams) -> list[dict[str, Any]]:
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
    return clauses


def _query(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    return {"bool": {"filter": clauses}}


def list_body(params: AlertListParams) -> dict[str, Any]:
    order = params.sort_order.value
    # Severity is a Snort priority where 1 is the most severe, so "most severe first"
    # (desc) sorts the number ascending.
    if params.sort_by is AlertSort.SEVERITY:
        order = "asc" if params.sort_order is SortOrder.DESC else "desc"
    return {
        "query": _query(filter_clauses(params)),
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


def pairs_body(filters: AlertFilterParams) -> dict[str, Any]:
    return _composite(
        _query(filter_clauses(filters)), [SOURCE_IP, TARGET_IP], with_latest=True
    )


def pair_rules_body(
    filters: AlertFilterParams, pairs: list[tuple[str, str]]
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
        _query([*filter_clauses(filters), on_page]),
        [SOURCE_IP, TARGET_IP, RULE_NAME],
        with_latest=True,
    )


def distinct_body(field: str) -> dict[str, Any]:
    return _composite(None, [field], with_latest=False)


def timeline_body(filters: AlertFilterParams, time_frame: TimeFrame) -> dict[str, Any]:
    histogram: dict[str, Any] = {
        "field": TIMESTAMP,
        "calendar_interval": _INTERVALS[time_frame],
        "time_zone": "UTC",
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
        "query": _query(filter_clauses(filters)),
        "aggs": {"rows": {"date_histogram": histogram}},
    }


def request_body(companion_id: str) -> dict[str, Any]:
    return {
        "query": {"ids": {"values": [companion_id]}},
        "size": 1,
        "_source": ["snort.http_request"],
    }
