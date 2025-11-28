from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from app.core.datetime_utils import ensure_timezone


class AgentInfo(BaseModel):
    name: str
    model: str
    version: str
    class_: str = Field(..., alias="class")
    latest_heartbeat_at: Optional[datetime] = None
    seconds_ago: int = Field(-1, description="Seconds since last heartbeat")
    heartbeat_interval: Optional[int] = Field(
        None, description="Configured heartbeat interval in seconds"
    )
    status: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("latest_heartbeat_at", mode="before")
    @classmethod
    def parse_heartbeat_time(cls, v):
        """Handle various heartbeat time formats from SQLAlchemy."""
        if v is None or v == "Never":
            return None
        if isinstance(v, str):
            # Parse string datetime if COALESCE forces string return
            try:
                from datetime import datetime as dt

                return dt.strptime(v, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
        return v

    @field_validator("model", "version", "class_", mode="before")
    @classmethod
    def empty_string_for_none(cls, v):
        """Convert None to empty string for string fields."""
        return v or ""

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        """Ensure status is valid."""
        valid_statuses = ["active", "inactive", "offline", "unknown"]
        if v and v in valid_statuses:
            return v
        return "unknown"


class HeartbeatNodeInfo(BaseModel):
    name: str
    os: str | None
    agents: list[AgentInfo]

    model_config = ConfigDict(from_attributes=True)


class HeartbeatTreeResponse(BaseModel):
    nodes: list[HeartbeatNodeInfo]
    total_nodes: int
    total_agents: int
    status_summary: Dict[str, int] | None = None

    model_config = ConfigDict(from_attributes=True)


class NodeInfo(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    ident: Optional[str] = None
    address: Optional[str] = None
    os: Optional[str] = None
    agents_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ProcessInfo(BaseModel):
    name: Optional[str] = None
    pid: Optional[int] = None
    path: Optional[str] = None
    args: List[str] = []
    env: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class AddressCategory(str, Enum):
    UNKNOWN = "unknown"
    ATM = "atm"
    EMAIL = "e-mail"
    LOTUS_NOTES = "lotus-notes"
    MAC = "mac"
    SNA = "sna"
    VM = "vm"
    IPV4_ADDR = "ipv4-addr"
    IPV4_ADDR_HEX = "ipv4-addr-hex"
    IPV4_NET = "ipv4-net"
    IPV4_NET_MASK = "ipv4-net-mask"
    IPV6_ADDR = "ipv6-addr"
    IPV6_ADDR_HEX = "ipv6-addr-hex"
    IPV6_NET = "ipv6-net"
    IPV6_NET_MASK = "ipv6-net-mask"


class NetworkInfo(BaseModel):
    interface: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    netmask: Optional[str] = None
    vlan_name: Optional[str] = None
    vlan_num: Optional[int] = None
    ident: Optional[str] = None
    ip_version: Optional[int] = None
    ip_hlen: Optional[int] = None
    protocol: Optional[str] = None
    protocol_number: Optional[int] = None
    node: Optional[NodeInfo] = None  # Node information for source/target
    heartbeat_process: Optional[ProcessInfo] = (
        None  # Process information from heartbeat
    )
    addresses: List[str] = []  # All addresses associated with this source/target

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class TimeInfo(BaseModel):
    """Simplified time info without IDMEF overhead."""

    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v):
        """Handle various timestamp inputs and ensure timezone-aware."""
        if v is None or v == 0:
            # Use current time for invalid timestamps
            from app.core.datetime_utils import get_current_time

            return get_current_time()

        if isinstance(v, datetime):
            return ensure_timezone(v)

        # Let Pydantic handle other types
        return v

    model_config = ConfigDict(from_attributes=True)


class ReferenceInfo(BaseModel):
    origin: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    meaning: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ServiceInfo(BaseModel):
    port: Optional[int] = None
    protocol: Optional[str] = None
    direction: str
    ip_version: Optional[int] = None
    name: Optional[str] = None
    iana_protocol_number: Optional[int] = None
    iana_protocol_name: Optional[str] = None
    portlist: Optional[str] = None
    ident: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnalyzerTimeInfo(BaseModel):
    """Simplified analyzer time without IDMEF overhead."""

    timestamp: datetime

    @field_validator("timestamp")
    def ensure_timezone_aware(cls, v):
        return ensure_timezone(v)

    model_config = ConfigDict(from_attributes=True)


class AnalyzerInfo(BaseModel):
    name: str
    analyzer_id: Optional[str] = None
    node: Optional[NodeInfo] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    version: Optional[str] = None
    class_type: Optional[str] = None
    ostype: Optional[str] = None
    osversion: Optional[str] = None
    process: Optional[ProcessInfo] = None
    analyzer_time: Optional[AnalyzerTimeInfo] = None
    chain_index: Optional[int] = None  # Position in analyzer chain
    role: Optional[str] = (
        None  # Role in analyzer chain (e.g., "Primary", "Concentrator")
    )

    model_config = ConfigDict(from_attributes=True)


class TableDeletionStats(BaseModel):
    """Number of rows deleted per table during alert cleanup."""

    table_name: str = Field(..., description="Name of the Prelude table")
    rows_deleted: int = Field(..., ge=0, description="Rows removed from the table")

    model_config = ConfigDict(from_attributes=True)


class WebServiceInfo(BaseModel):
    url: str
    cgi: Optional[str] = None
    http_method: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AlertIdentInfo(BaseModel):
    alertident: str
    analyzerid: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TCPInfo(BaseModel):
    seq: Optional[str] = Field(None, alias="tcp_seq")
    ack: Optional[str] = Field(None, alias="tcp_ack")
    off: Optional[str] = Field(None, alias="tcp_off")
    res: Optional[str] = Field(None, alias="tcp_res")
    flags: Optional[str] = Field(None, alias="tcp_flags")
    win: Optional[str] = Field(None, alias="tcp_win")
    sum: Optional[str] = Field(None, alias="tcp_sum")
    urp: Optional[str] = Field(None, alias="tcp_urp")


class IPInfo(BaseModel):
    ver: Optional[str] = Field(None, alias="ip_ver")
    hlen: Optional[str] = Field(None, alias="ip_hlen")
    tos: Optional[str] = Field(None, alias="ip_tos")
    len: Optional[str] = Field(None, alias="ip_len")
    id: Optional[str] = Field(None, alias="ip_id")
    off: Optional[str] = Field(None, alias="ip_off")
    ttl: Optional[str] = Field(None, alias="ip_ttl")
    proto: Optional[str] = Field(None, alias="ip_proto")
    sum: Optional[str] = Field(None, alias="ip_sum")


class SnortInfo(BaseModel):
    rule_sid: Optional[str] = Field(None, alias="snort_rule_sid")
    rule_rev: Optional[str] = Field(None, alias="snort_rule_rev")


class AlertListItem(BaseModel):
    id: str
    message_id: str
    created_at: Optional[TimeInfo] = None
    detected_at: TimeInfo
    classification_text: Optional[str] = None
    severity: Optional[str] = None
    source_ipv4: Optional[str] = None
    target_ipv4: Optional[str] = None
    analyzer: Optional[AnalyzerInfo] = None
    correlation_description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    items: List[AlertListItem]
    pagination: PaginatedResponse

    model_config = ConfigDict(from_attributes=True)


class AlertDetail(BaseModel):
    id: str
    message_id: str
    created_at: Optional[TimeInfo] = None
    detected_at: TimeInfo
    classification_text: Optional[str] = None
    classification_ident: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    completion: Optional[str] = None
    impact_type: Optional[str] = None
    source: Optional[NetworkInfo] = None
    target: Optional[NetworkInfo] = None
    analyzers: List[AnalyzerInfo] = []  # Changed from single analyzer to list
    references: List[ReferenceInfo] = []
    services: List[ServiceInfo] = []
    web_services: List[WebServiceInfo] = []
    alert_idents: List[AlertIdentInfo] = []
    additional_data: dict = {}
    correlation_description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @property
    def tcp_info(self) -> Optional[TCPInfo]:
        """Extract TCP-related information from additional_data"""
        if not any(k.startswith("tcp_") for k in self.additional_data.keys()):
            return None
        return TCPInfo(
            **{k: v for k, v in self.additional_data.items() if k.startswith("tcp_")}
        )

    @property
    def ip_info(self) -> Optional[IPInfo]:
        """Extract IP-related information from additional_data"""
        if not any(k.startswith("ip_") for k in self.additional_data.keys()):
            return None
        return IPInfo(
            **{k: v for k, v in self.additional_data.items() if k.startswith("ip_")}
        )

    @property
    def snort_info(self) -> Optional[SnortInfo]:
        """Extract Snort-related information from additional_data"""
        if not any(k.startswith("snort_") for k in self.additional_data.keys()):
            return None
        return SnortInfo(
            **{k: v for k, v in self.additional_data.items() if k.startswith("snort_")}
        )


class TimelineDataPoint(BaseModel):
    timestamp: datetime
    total: int
    by_severity: Dict[str, int]
    by_classification: Dict[str, int]
    by_analyzer: Dict[str, int]

    @field_validator("timestamp")
    def ensure_timezone_aware(cls, v):
        return ensure_timezone(v)

    model_config = ConfigDict(from_attributes=True)


class TimelineResponse(BaseModel):
    time_frame: str
    start_date: datetime
    end_date: datetime
    data: List[TimelineDataPoint]

    @field_validator("start_date", "end_date")
    def ensure_timezone_aware(cls, v):
        return ensure_timezone(v)

    model_config = ConfigDict(from_attributes=True)


class GroupedAlertDetail(BaseModel):
    classification: str
    count: int
    analyzer: List[str]
    analyzer_host: List[str]
    detected_at: datetime


class GroupedAlert(BaseModel):
    source_ipv4: Optional[str] = None
    target_ipv4: Optional[str] = None
    total_count: int
    alerts: List[GroupedAlertDetail]


class GroupedAlertResponse(BaseModel):
    groups: List[GroupedAlert] = Field(..., description="List of grouped alerts")
    pagination: PaginatedResponse
    total_alerts: int = Field(
        ...,
        description="Total number of individual alerts across all groups on current page",
    )

    model_config = ConfigDict(from_attributes=True)


class StatisticsSummary(BaseModel):
    total_alerts: int
    alerts_by_severity: Dict[str, int]
    alerts_by_classification: Dict[str, int]
    alerts_by_analyzer: Dict[str, int]
    alerts_by_source_ip: Dict[str, int]
    alerts_by_target_ip: Dict[str, int]
    time_range_hours: int
    start_at: datetime
    end_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HeartbeatStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class HeartbeatListItem(BaseModel):
    id: int = Field(..., description="Heartbeat ID")
    message_id: Optional[str] = Field(None, description="Message ID")
    heartbeat_interval: Optional[int] = Field(
        None, description="Heartbeat interval in seconds"
    )
    analyzer: AnalyzerInfo
    node: NodeInfo
    latest_heartbeat_at: datetime = Field(..., description="Last heartbeat timestamp")
    status: HeartbeatStatus = Field(..., description="Current status (online/offline)")

    model_config = ConfigDict(from_attributes=True)


class HeartbeatListResponse(BaseModel):
    items: List[HeartbeatListItem]
    total: int
    page: int
    size: int

    model_config = ConfigDict(from_attributes=True)


class HeartbeatDetail(HeartbeatListItem):
    analyzer: AnalyzerInfo  # Extended analyzer info with OS details

    model_config = ConfigDict(from_attributes=True)


class HeartbeatTreeItem(BaseModel):
    name: str
    model: str
    version: str
    class_: str = Field(..., alias="class")
    last_heartbeat_at: str
    status: str
    node_location: str

    model_config = ConfigDict(from_attributes=True)


class HostInfo(BaseModel):
    os: str | None
    analyzers: list[AnalyzerInfo]


class HeartbeatTimelineItem(BaseModel):
    timestamp: datetime
    host_name: str
    analyzer_name: str
    model: str
    version: str
    class_: str

    model_config = ConfigDict(from_attributes=True)


class TreeAgentInfo(BaseModel):
    name: str
    model: str
    version: str
    class_: str = Field(..., alias="class")
    last_heartbeat_at: datetime | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class TreeHostInfo(BaseModel):
    os: str | None
    agents: list[TreeAgentInfo]

    model_config = ConfigDict(from_attributes=True)


class PaginatedHeartbeatTimelineResponse(BaseModel):
    items: List[HeartbeatTimelineItem]
    pagination: PaginatedResponse

    model_config = ConfigDict(from_attributes=True)
