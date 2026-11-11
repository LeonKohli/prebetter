from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TimeInfo(BaseModel):
    timestamp: datetime


class AnalyzerInfo(BaseModel):
    name: str | None = None
    interface: str | None = None


class AlertListItem(BaseModel):
    id: str
    detected_at: TimeInfo
    severity: str | None = None
    classification_text: str | None = None
    source_ipv4: str | None = None
    target_ipv4: str | None = None
    analyzer: AnalyzerInfo


class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int


class AlertListResponse(BaseModel):
    items: list[AlertListItem]
    pagination: PaginatedResponse


class RuleInfo(BaseModel):
    id: str | None = None
    version: str | None = None
    category: str | None = None


class Endpoint(BaseModel):
    address: str
    port: int | None = None
    mac: str | None = None


class NetworkInfo(BaseModel):
    transport: str | None = None
    protocol: str | None = None
    vlan_id: str | None = None
    bytes: int | None = None
    packets: int | None = None


class FlowInfo(BaseModel):
    direction: str | None = None
    started_at: datetime | None = None
    client_bytes: int | None = None
    client_packets: int | None = None
    server_bytes: int | None = None
    server_packets: int | None = None


class ForwardedInfo(BaseModel):
    """Client address from the proxied request's X-Forwarded-For header (advisory)."""

    true_source: str | None = None
    forwarded_for: list[str] = []  # whole chain, left to right
    via_proxy: str | None = None  # first Via header value


class AlertDetail(BaseModel):
    id: str
    detected_at: TimeInfo
    severity: str | None = None
    classification_text: str | None = None
    rule: RuleInfo
    action: str | None = None
    source: Endpoint | None = None
    target: Endpoint | None = None
    network: NetworkInfo
    flow: FlowInfo
    analyzer: AnalyzerInfo
    # Snort's packet fields ("pkt_len", "ip_ttl"); which ones exist varies per alert.
    packet: dict[str, str | int | float | bool]
    # Base64 of the bytes the rule matched on; absent when the sensor does not log payloads.
    payload: str | None = None
    # Absent without a payload or an X-Forwarded-For header in it.
    forwarded: ForwardedInfo | None = None
    # Decoded request line ("GET /path HTTP/1.1"); absent without a companion document.
    http_request: str | None = None
    document: dict[str, Any]


class GroupedAlertDetail(BaseModel):
    classification: str
    count: int
    detected_at: datetime


class GroupedAlert(BaseModel):
    source_ipv4: str
    target_ipv4: str
    total_count: int
    alerts: list[GroupedAlertDetail]


class GroupedAlertResponse(BaseModel):
    groups: list[GroupedAlert]
    pagination: PaginatedResponse
    total_alerts: int


class TimelineDataPoint(BaseModel):
    timestamp: datetime
    total: int


class BaselinePoint(BaseModel):
    """Typical range of one hour, from the same hour of earlier weeks."""

    timestamp: datetime
    low: int
    high: int
    typical: float


class TimelineResponse(BaseModel):
    time_frame: str
    start_date: datetime
    end_date: datetime
    data: list[TimelineDataPoint]
    # Hourly buckets only; hours without enough history are left out.
    baseline: list[BaselinePoint] = []
