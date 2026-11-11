import ipaddress
from typing import Any

from fastapi import HTTPException
from opensearchpy import AsyncOpenSearch

from app.opensearch import documents, queries
from app.opensearch.documents import Pair
from app.opensearch.request_line import decode_request_line, request_id
from app.schemas.alerts import (
    AlertDetail,
    AlertListItem,
    GroupedAlert,
    GroupedAlertDetail,
    TimelineDataPoint,
)
from app.schemas.filters import (
    AlertFilterParams,
    AlertListParams,
    GroupListParams,
    GroupSort,
    SortOrder,
    TimeFrame,
)

MAX_PAIRS = 50_000


def _address_key(address: str) -> tuple[int, int]:
    """IPv4 before IPv6, numeric within a version (mixed versions do not compare)."""
    ip = ipaddress.ip_address(address)
    return ip.version, int(ip)


def _sort_pairs(pairs: list[Pair], sort_by: GroupSort, sort_order: SortOrder) -> None:
    keys = {
        GroupSort.TOTAL_COUNT: lambda p: p.count,
        GroupSort.DETECT_TIME: lambda p: p.latest,
        GroupSort.SOURCE_IP: lambda p: _address_key(p.source),
        GroupSort.TARGET_IP: lambda p: _address_key(p.target),
    }
    # Sorts are stable: the pair order below survives as the tie-break in both directions.
    pairs.sort(key=lambda p: (_address_key(p.source), _address_key(p.target)))
    pairs.sort(key=keys[sort_by], reverse=sort_order is SortOrder.DESC)


class AlertRepository:
    """Read-only access to the alert indices; the only code that talks to OpenSearch."""

    def __init__(self, client: AsyncOpenSearch, index: str, request_index: str):
        self._client = client
        self._index = index
        self._request_index = request_index

    async def _search(self, body: dict[str, Any]) -> dict[str, Any]:
        return await self._client.search(index=self._index, body=body)

    async def _buckets(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        """Buckets of the aggregation `rows`."""
        response = await self._search(body)
        # A pattern that matches no index yet answers without an aggregations section.
        return response.get("aggregations", {}).get("rows", {}).get("buckets", [])

    async def _composite(
        self, body: dict[str, Any], max_buckets: int | None = None
    ) -> list[dict[str, Any]]:
        """Follow `after_key` until the composite aggregation `rows` is exhausted."""
        composite = body["aggs"]["rows"]["composite"]
        buckets: list[dict[str, Any]] = []
        while True:
            page = await self._buckets(body)
            buckets += page
            if max_buckets is not None and len(buckets) > max_buckets:
                raise HTTPException(
                    status_code=422,
                    detail="Too many address pairs, narrow the filter",
                )
            if len(page) < composite["size"]:
                return buckets
            # The key of the last bucket is where the next page starts.
            composite["after"] = page[-1]["key"]

    async def list_alerts(
        self, params: AlertListParams
    ) -> tuple[list[AlertListItem], int]:
        response = await self._search(queries.list_body(params))
        hits = response["hits"]
        return [documents.to_list_item(h) for h in hits["hits"]], hits["total"]["value"]

    async def group_alerts(
        self, params: GroupListParams
    ) -> tuple[list[GroupedAlert], int]:
        """One page of address pairs with their rule counts, and the number of pairs."""
        buckets = await self._composite(queries.pairs_body(params), MAX_PAIRS)
        pairs = [documents.to_pair(b) for b in buckets]
        _sort_pairs(pairs, params.sort_by, params.sort_order)
        page = pairs[params.offset : params.offset + params.size]
        if not page:
            return [], len(pairs)

        body = queries.pair_rules_body(params, [(p.source, p.target) for p in page])
        rules: dict[tuple[str, str], list[GroupedAlertDetail]] = {}
        for bucket in await self._composite(body):
            key = bucket["key"]
            pair_key = (key["source.ip"], key["destination.ip"])
            rules.setdefault(pair_key, []).append(documents.to_group_detail(bucket))
        groups = []
        for pair in page:
            alerts = rules.get((pair.source, pair.target), [])
            alerts.sort(key=lambda a: a.classification)
            alerts.sort(key=lambda a: a.detected_at, reverse=True)
            groups.append(
                GroupedAlert(
                    source_ipv4=pair.source,
                    target_ipv4=pair.target,
                    total_count=pair.count,
                    alerts=alerts,
                )
            )
        return groups, len(pairs)

    async def get_alert(self, alert_id: str) -> AlertDetail | None:
        body = {"query": {"term": {"event.id": alert_id}}, "size": 1}
        hits = (await self._search(body))["hits"]["hits"]
        if not hits:
            return None
        return documents.to_detail(
            hits[0], await self._http_request(hits[0]["_source"])
        )

    async def _http_request(self, alert: dict[str, Any]) -> str | None:
        """Request line from the alert's companion document, if it has one."""
        companion_id = request_id(alert)
        if companion_id is None:
            return None
        response = await self._client.search(
            index=self._request_index,
            body=queries.request_body(companion_id),
        )
        hits = response["hits"]["hits"]
        if not hits:
            return None
        return decode_request_line(
            hits[0]["_source"].get("snort", {}).get("http_request")
        )

    async def timeline(
        self, filters: AlertFilterParams, time_frame: TimeFrame
    ) -> list[TimelineDataPoint]:
        buckets = await self._buckets(queries.timeline_body(filters, time_frame))
        return [documents.to_timeline_point(b) for b in buckets]

    async def sensors(self) -> list[str]:
        buckets = await self._composite(queries.distinct_body(queries.SENSOR))
        return [b["key"][queries.SENSOR] for b in buckets]

    async def rule_names(self) -> list[str]:
        buckets = await self._composite(queries.distinct_body(queries.RULE_NAME))
        return [b["key"][queries.RULE_NAME] for b in buckets]

    async def count(self, timeout: float | None = None) -> int:
        """Number of documents in the index pattern."""
        response = await self._client.count(
            index=self._index, params={"request_timeout": timeout}
        )
        return response["count"]
