from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from enum import Enum
from app.core.datetime_utils import ensure_timezone


class AgentInfo(BaseModel):
    name: str
    model: str
    version: str
    class_: str = Field(..., alias="class")
    latest_heartbeat_at: datetime | None = None
    seconds_ago: int = Field(-1, description="Seconds since last heartbeat")
    heartbeat_interval: int | None = Field(
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
    status_summary: dict[str, int] | None = None

    model_config = ConfigDict(from_attributes=True)


class NodeInfo(BaseModel):
    name: str | None = None
    location: str | None = None
    category: str | None = None
    ident: str | None = None
    address: str | None = None
    os: str | None = None
    agents_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ProcessInfo(BaseModel):
    name: str | None = None
    pid: int | None = None
    path: str | None = None
    args: list[str] = []
    env: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class NetworkInfo(BaseModel):
    interface: str | None = None
    category: str | None = None
    address: str | None = None
    netmask: str | None = None
    vlan_name: str | None = None
    vlan_num: int | None = None
    ident: str | None = None
    ip_version: int | None = None
    ip_hlen: int | None = None
    protocol: str | None = None
    protocol_number: int | None = None
    node: NodeInfo | None = None  # Node information for source/target
    heartbeat_process: ProcessInfo | None = None  # Process information from heartbeat
    addresses: list[str] = []  # All addresses associated with this source/target

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
    origin: str | None = None
    name: str | None = None
    url: str | None = None
    meaning: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ServiceInfo(BaseModel):
    port: int | None = None
    protocol: str | None = None
    direction: str
    ip_version: int | None = None
    name: str | None = None
    iana_protocol_number: int | None = None
    iana_protocol_name: str | None = None
    portlist: str | None = None
    ident: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalyzerTimeInfo(BaseModel):
    """Simplified analyzer time without IDMEF overhead."""

    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def ensure_timezone_aware(cls, v):
        return ensure_timezone(v)

    model_config = ConfigDict(from_attributes=True)


class AnalyzerInfo(BaseModel):
    name: str
    analyzer_id: str | None = None
    node: NodeInfo | None = None
    model: str | None = None
    manufacturer: str | None = None
    version: str | None = None
    class_type: str | None = None
    ostype: str | None = None
    osversion: str | None = None
    process: ProcessInfo | None = None
    analyzer_time: AnalyzerTimeInfo | None = None
    chain_index: int | None = None  # Position in analyzer chain
    role: str | None = None  # Role in analyzer chain (e.g., "Primary", "Concentrator")

    model_config = ConfigDict(from_attributes=True)


class WebServiceInfo(BaseModel):
    url: str
    cgi: str | None = None
    http_method: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AlertIdentInfo(BaseModel):
    alertident: str
    analyzerid: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AlertListItem(BaseModel):
    id: str
    message_id: str
    created_at: TimeInfo | None = None
    detected_at: TimeInfo
    classification_text: str | None = None
    severity: str | None = None
    source_ipv4: str | None = None
    target_ipv4: str | None = None
    analyzer: AnalyzerInfo | None = None
    correlation_description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    items: list[AlertListItem]
    pagination: PaginatedResponse

    model_config = ConfigDict(from_attributes=True)


class AlertDetail(BaseModel):
    id: str
    message_id: str
    created_at: TimeInfo | None = None
    detected_at: TimeInfo
    classification_text: str | None = None
    classification_ident: str | None = None
    severity: str | None = None
    description: str | None = None
    completion: str | None = None
    impact_type: str | None = None
    source: NetworkInfo | None = None
    target: NetworkInfo | None = None
    analyzers: list[AnalyzerInfo] = []  # Changed from single analyzer to list
    references: list[ReferenceInfo] = []
    services: list[ServiceInfo] = []
    web_services: list[WebServiceInfo] = []
    alert_idents: list[AlertIdentInfo] = []
    additional_data: dict = {}
    correlation_description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TimelineDataPoint(BaseModel):
    timestamp: datetime
    total: int
    by_severity: dict[str, int]
    by_classification: dict[str, int]
    by_analyzer: dict[str, int]

    @field_validator("timestamp")
    @classmethod
    def ensure_timezone_aware(cls, v):
        return ensure_timezone(v)

    model_config = ConfigDict(from_attributes=True)


class TimelineResponse(BaseModel):
    time_frame: str
    start_date: datetime
    end_date: datetime
    data: list[TimelineDataPoint]

    @field_validator("start_date", "end_date")
    @classmethod
    def ensure_timezone_aware(cls, v):
        return ensure_timezone(v)

    model_config = ConfigDict(from_attributes=True)


class GroupedAlertDetail(BaseModel):
    classification: str
    count: int
    analyzer: list[str]
    analyzer_host: list[str]
    detected_at: datetime


class GroupedAlert(BaseModel):
    source_ipv4: str | None = None
    target_ipv4: str | None = None
    total_count: int
    alerts: list[GroupedAlertDetail]


class GroupedAlertResponse(BaseModel):
    groups: list[GroupedAlert] = Field(..., description="List of grouped alerts")
    pagination: PaginatedResponse
    total_alerts: int = Field(
        ...,
        description="Total number of individual alerts across all groups on current page",
    )

    model_config = ConfigDict(from_attributes=True)


class AlertDeletionResponse(BaseModel):
    deleted: int = Field(description="Number of alerts deleted")
    rows: int = Field(description="Total number of database rows deleted")


class StatisticsSummary(BaseModel):
    total_alerts: int
    alerts_by_severity: dict[str, int]
    alerts_by_classification: dict[str, int]
    alerts_by_analyzer: dict[str, int]
    alerts_by_source_ip: dict[str, int]
    alerts_by_target_ip: dict[str, int]
    time_range_hours: int
    start_at: datetime
    end_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HeartbeatStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class HeartbeatListItem(BaseModel):
    id: int = Field(..., description="Heartbeat ID")
    message_id: str | None = Field(None, description="Message ID")
    heartbeat_interval: int | None = Field(
        None, description="Heartbeat interval in seconds"
    )
    analyzer: AnalyzerInfo
    node: NodeInfo
    latest_heartbeat_at: datetime = Field(..., description="Last heartbeat timestamp")
    status: HeartbeatStatus = Field(..., description="Current status (online/offline)")

    model_config = ConfigDict(from_attributes=True)


class HeartbeatListResponse(BaseModel):
    items: list[HeartbeatListItem]
    total: int
    page: int
    size: int

    model_config = ConfigDict(from_attributes=True)


class HeartbeatTimelineItem(BaseModel):
    timestamp: datetime
    host_name: str
    analyzer_name: str
    model: str
    version: str
    class_: str

    model_config = ConfigDict(from_attributes=True)


class PaginatedHeartbeatTimelineResponse(BaseModel):
    items: list[HeartbeatTimelineItem]
    pagination: PaginatedResponse

    model_config = ConfigDict(from_attributes=True)
