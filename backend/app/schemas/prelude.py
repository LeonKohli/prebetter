from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Literal
from datetime import datetime, UTC
from enum import Enum


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
    interface: Optional[str]
    ip_version: Optional[int]
    ip_hlen: Optional[int]
    category: AddressCategory = Field(..., description="Network address category")
    address: str = Field(..., description="Network address (IPv4, IPv6, etc.)")
    netmask: Optional[str] = Field(None, description="Network mask")
    vlan_name: Optional[str] = Field(None, description="VLAN name if applicable")
    vlan_num: Optional[int] = Field(None, description="VLAN number if applicable")
    ident: Optional[str] = Field(None, description="Address identifier")

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class TimeInfo(BaseModel):
    time: datetime = Field(..., description="Timestamp of the event")
    usec: int = Field(..., description="Microseconds part of the timestamp")
    gmtoff: int = Field(..., description="GMT offset in seconds")

    model_config = ConfigDict(from_attributes=True)


class ReferenceInfo(BaseModel):
    origin: str = Field(
        ..., description="Origin of the reference (e.g., 'vendor-specific', 'cve')"
    )
    name: str = Field(..., description="Reference identifier or name")
    url: Optional[str] = Field(None, description="URL for more information")
    meaning: Optional[str] = Field(
        None, description="Additional context about the reference"
    )

    model_config = ConfigDict(from_attributes=True)


class ServiceInfo(BaseModel):
    port: Optional[int] = Field(None, description="Port number")
    protocol: str = Field(..., description="Protocol name (e.g., 'tcp', 'udp')")
    direction: str = Field(..., description="Traffic direction ('source' or 'target')")

    model_config = ConfigDict(from_attributes=True)


class NodeInfo(BaseModel):
    ident: Optional[str] = Field(None, description="Node identifier")
    category: Optional[str] = Field(None, description="Node category (e.g., 'unknown')")
    location: Optional[str] = Field(None, description="Physical or logical location")
    name: Optional[str] = Field(None, description="Node hostname or name")

    model_config = ConfigDict(from_attributes=True)


class ProcessInfo(BaseModel):
    name: Optional[str] = Field(None, description="Process name")
    pid: Optional[int] = Field(None, description="Process ID")
    path: Optional[str] = Field(None, description="Process executable path")

    model_config = ConfigDict(from_attributes=True)


class AnalyzerInfo(BaseModel):
    name: str = Field(..., description="Analyzer name (e.g., 'snort-eno5')")
    node: Optional[NodeInfo] = Field(None, description="Node information")
    model: Optional[str] = Field(None, description="Analyzer model (e.g., 'Snort')")
    manufacturer: Optional[str] = Field(None, description="Manufacturer information")
    version: Optional[str] = Field(None, description="Software version")
    class_type: Optional[str] = Field(None, description="Analyzer class (e.g., 'NIDS')")
    ostype: Optional[str] = Field(None, description="Operating system type")
    osversion: Optional[str] = Field(None, description="Operating system version")
    process: Optional[ProcessInfo] = Field(None, description="Process information")

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
    alert_id: int = Field(..., description="Unique alert identifier")
    message_id: Optional[str] = Field(None, description="Message identifier")
    create_time: Optional[TimeInfo] = Field(None, description="Alert creation time")
    detect_time: TimeInfo = Field(..., description="Alert detection time")
    classification_text: str = Field(
        ..., description="Alert classification description"
    )
    severity: Optional[str] = Field(None, description="Alert severity level")
    source_ipv4: Optional[str] = Field(None, description="Source IPv4 address")
    target_ipv4: Optional[str] = Field(None, description="Target IPv4 address")
    analyzer: Optional[AnalyzerInfo] = Field(None, description="Analyzer information")

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    total: int = Field(..., description="Total number of alerts")
    items: List[AlertListItem] = Field(..., description="List of alerts")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")


class AlertDetail(BaseModel):
    alert_id: int = Field(..., description="Unique alert identifier")
    message_id: Optional[str] = Field(None, description="Message identifier")
    create_time: Optional[TimeInfo] = Field(None, description="Alert creation time")
    detect_time: TimeInfo = Field(..., description="Alert detection time")
    classification_text: str = Field(
        ..., description="Alert classification description"
    )
    classification_ident: Optional[str] = Field(
        None, description="Classification identifier"
    )
    severity: Optional[str] = Field(None, description="Alert severity level")
    description: Optional[str] = Field(None, description="Detailed alert description")
    completion: Optional[str] = Field(None, description="Alert completion status")
    impact_type: Optional[str] = Field(None, description="Type of impact")

    source: Optional[NetworkInfo] = Field(
        None, description="Source network information"
    )
    target: Optional[NetworkInfo] = Field(
        None, description="Target network information"
    )

    analyzer: Optional[AnalyzerInfo] = Field(None, description="Analyzer information")
    references: List[ReferenceInfo] = Field(
        default_factory=list, description="Related references"
    )
    services: List[ServiceInfo] = Field(
        default_factory=list, description="Network services involved"
    )

    additional_data: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Additional alert data including payload and protocol details",
    )

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
    time: datetime = Field(..., description="Time bucket for the data point")
    count: int = Field(..., description="Number of alerts in this time bucket")


class TimelineResponse(BaseModel):
    data: List[TimelineDataPoint] = Field(..., description="List of data points for the timeline")


class GroupedAlertDetail(BaseModel):
    classification: str = Field(..., description="Classification text")
    count: int = Field(..., description="Number of alerts for this classification")
    analyzer: List[str] = Field(..., description="List of analyzer names")
    analyzer_host: List[str] = Field(..., description="List of analyzer host names")
    time: datetime = Field(..., description="Time of the most recent alert")


class GroupedAlert(BaseModel):
    source_ipv4: str = Field(..., description="Source IPv4 address")
    target_ipv4: str = Field(..., description="Target IPv4 address")
    total_count: int = Field(..., description="Total number of alerts in this group")
    alerts: List[GroupedAlertDetail] = Field(..., description="Detailed alert information for this group")


class GroupedAlertResponse(BaseModel):
    total: int = Field(..., description="Total number of groups")
    groups: List[GroupedAlert] = Field(..., description="List of grouped alerts")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of groups per page")

    model_config = ConfigDict(from_attributes=True)
