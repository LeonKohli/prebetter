"""
Maps OpenSearch documents and buckets to the response models. The only place that
knows both sides of the wire names the frontend uses:

    id                      <- _id (equals event.id)
    detected_at.timestamp   <- @timestamp
    severity                <- event.severity (labels below)
    classification_text     <- rule.name
    source_ipv4/target_ipv4 <- source.ip / destination.ip
    analyzer.name           <- observer.name
    analyzer.interface      <- observer.ingress.interface.name
    flow.*                  <- snort.dir, event.start, client.*, server.*
    packet                  <- snort.* (flattened)
    payload                 <- snort.b64_data
    forwarded               <- X-Forwarded-For and Via in snort.b64_data (forwarded.py)
    http_request            <- snort.http_request of the companion document in the
                               request indices (request_line.py)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.opensearch.forwarded import forwarded_info
from app.schemas.alerts import (
    AlertDetail,
    AlertListItem,
    AnalyzerInfo,
    Endpoint,
    FlowInfo,
    GroupedAlertDetail,
    NetworkInfo,
    RuleInfo,
    TimeInfo,
    TimelineDataPoint,
)

_BY_PRIORITY = {0: "high", 1: "high", 2: "medium", 3: "low"}

# Priority 0 is as severe as 1; anything from 4 up is informational.
_SEVERITY_CLAUSES: dict[str, dict[str, Any]] = {
    "high": {"range": {"event.severity": {"gte": 0, "lte": 1}}},
    "medium": {"term": {"event.severity": 2}},
    "low": {"term": {"event.severity": 3}},
    "info": {"range": {"event.severity": {"gte": 4}}},
}


def severity_label(priority: int | None) -> str | None:
    if priority is None:
        return None
    return _BY_PRIORITY.get(priority, "info")


def severity_filter(labels: list[str]) -> dict[str, Any]:
    """Match any of the given labels."""
    return {
        "bool": {
            "should": [_SEVERITY_CLAUSES[label] for label in labels],
            "minimum_should_match": 1,
        }
    }


def _dig(doc: dict[str, Any], path: str) -> Any:
    """Read a dotted ECS field name from the nested `_source`."""
    value: Any = doc
    for key in path.split("."):
        if value is None:
            return None
        value = value.get(key)
    return value


def _analyzer(src: dict[str, Any]) -> AnalyzerInfo:
    return AnalyzerInfo(
        name=_dig(src, "observer.name"),
        interface=_dig(src, "observer.ingress.interface.name"),
    )


def to_list_item(hit: dict[str, Any]) -> AlertListItem:
    src = hit["_source"]
    return AlertListItem(
        id=hit["_id"],
        detected_at=TimeInfo(timestamp=src["@timestamp"]),
        severity=severity_label(_dig(src, "event.severity")),
        classification_text=_dig(src, "rule.name"),
        source_ipv4=_dig(src, "source.ip"),
        target_ipv4=_dig(src, "destination.ip"),
        analyzer=AnalyzerInfo(name=_dig(src, "observer.name")),
    )


def _endpoint(src: dict[str, Any], side: str) -> Endpoint | None:
    address = _dig(src, f"{side}.ip")
    if address is None:
        return None
    return Endpoint(
        address=address, port=_dig(src, f"{side}.port"), mac=_dig(src, f"{side}.mac")
    )


# Already shown as addresses and ports, interface, rule id, flow direction and payload.
_PACKET_DUPLICATES = {"src_ap", "dst_ap", "iface", "rule", "dir", "b64_data"}


def _flatten(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """{"ip": {"ttl": 64}} -> {"ip_ttl": 64}"""
    flat: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            flat |= _flatten(item, f"{prefix}{key}_")
        else:
            flat[f"{prefix}{key}"] = item
    return flat


def _packet(src: dict[str, Any]) -> dict[str, Any]:
    fields = {
        key: value
        for key, value in src.get("snort", {}).items()
        if key not in _PACKET_DUPLICATES
    }
    return _flatten(fields)


def to_detail(hit: dict[str, Any], http_request: str | None = None) -> AlertDetail:
    src = hit["_source"]
    payload = _dig(src, "snort.b64_data")
    return AlertDetail(
        id=hit["_id"],
        detected_at=TimeInfo(timestamp=src["@timestamp"]),
        severity=severity_label(_dig(src, "event.severity")),
        classification_text=_dig(src, "rule.name"),
        rule=RuleInfo(
            id=_dig(src, "rule.id"),
            version=_dig(src, "rule.version"),
            category=_dig(src, "rule.category"),
        ),
        action=_dig(src, "event.action"),
        source=_endpoint(src, "source"),
        target=_endpoint(src, "destination"),
        network=NetworkInfo(
            transport=_dig(src, "network.transport"),
            protocol=_dig(src, "network.protocol"),
            vlan_id=_dig(src, "network.vlan.id"),
            bytes=_dig(src, "network.bytes"),
            packets=_dig(src, "network.packets"),
        ),
        flow=FlowInfo(
            direction=_dig(src, "snort.dir"),
            started_at=_dig(src, "event.start"),
            client_bytes=_dig(src, "client.bytes"),
            client_packets=_dig(src, "client.packets"),
            server_bytes=_dig(src, "server.bytes"),
            server_packets=_dig(src, "server.packets"),
        ),
        analyzer=_analyzer(src),
        packet=_packet(src),
        payload=payload,
        forwarded=forwarded_info(payload),
        http_request=http_request,
        document=src,
    )


@dataclass(frozen=True)
class Pair:
    """One (source, destination) address pair from the composite enumeration."""

    source: str
    target: str
    count: int
    latest: datetime


def to_pair(bucket: dict[str, Any]) -> Pair:
    key = bucket["key"]
    return Pair(
        source=key["source.ip"],
        target=key["destination.ip"],
        count=bucket["doc_count"],
        latest=datetime.fromisoformat(bucket["latest"]["value_as_string"]),
    )


def to_timeline_point(bucket: dict[str, Any]) -> TimelineDataPoint:
    return TimelineDataPoint(
        timestamp=datetime.fromisoformat(bucket["key_as_string"]),
        total=bucket["doc_count"],
    )


def to_group_detail(bucket: dict[str, Any]) -> GroupedAlertDetail:
    return GroupedAlertDetail(
        classification=bucket["key"]["rule.name"],
        count=bucket["doc_count"],
        detected_at=datetime.fromisoformat(bucket["latest"]["value_as_string"]),
    )
