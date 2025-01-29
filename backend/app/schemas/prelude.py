from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime
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
    interface: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    netmask: Optional[str] = None
    vlan_name: Optional[str] = None
    vlan_num: Optional[int] = None
    ident: Optional[str] = None
    ip_version: Optional[int] = None
    ip_hlen: Optional[int] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class TimeInfo(BaseModel):
    time: datetime
    usec: Optional[int] = None
    gmtoff: Optional[int] = None

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

    model_config = ConfigDict(from_attributes=True)


class NodeInfo(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    ident: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProcessInfo(BaseModel):
    name: Optional[str] = None
    pid: Optional[int] = None
    path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnalyzerInfo(BaseModel):
    name: str
    node: Optional[NodeInfo] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    version: Optional[str] = None
    class_type: Optional[str] = None
    ostype: Optional[str] = None
    osversion: Optional[str] = None
    process: Optional[ProcessInfo] = None

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
    alert_id: str
    message_id: str
    create_time: Optional[TimeInfo] = None
    detect_time: TimeInfo
    classification_text: Optional[str] = None
    severity: Optional[str] = None
    source_ipv4: Optional[str] = None
    target_ipv4: Optional[str] = None
    analyzer: Optional[AnalyzerInfo] = None

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    total: int
    items: List[AlertListItem]
    page: int
    size: int


class AlertDetail(BaseModel):
    alert_id: str
    message_id: str
    create_time: Optional[TimeInfo] = None
    detect_time: TimeInfo
    classification_text: Optional[str] = None
    classification_ident: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    completion: Optional[str] = None
    impact_type: Optional[str] = None
    source: Optional[NetworkInfo] = None
    target: Optional[NetworkInfo] = None
    analyzer: Optional[AnalyzerInfo] = None
    references: List[ReferenceInfo] = []
    services: List[ServiceInfo] = []
    additional_data: dict = {}

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

    model_config = ConfigDict(from_attributes=True)


class TimelineResponse(BaseModel):
    time_frame: str
    start_date: datetime
    end_date: datetime
    data: List[TimelineDataPoint]

    model_config = ConfigDict(from_attributes=True)


class GroupedAlertDetail(BaseModel):
    classification: str
    count: int
    analyzer: List[str]
    analyzer_host: List[str]
    time: datetime


class GroupedAlert(BaseModel):
    source_ipv4: Optional[str] = None
    target_ipv4: Optional[str] = None
    total_count: int
    alerts: List[GroupedAlertDetail]


class GroupedAlertResponse(BaseModel):
    total: int
    groups: List[GroupedAlert]
    page: int
    size: int

    total: int = Field(..., description="Total number of groups")
    groups: List[GroupedAlert] = Field(..., description="List of grouped alerts")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of groups per page")

    model_config = ConfigDict(from_attributes=True)


class StatisticsSummary(BaseModel):
    total_alerts: int
    alerts_by_severity: Dict[str, int]
    alerts_by_classification: Dict[str, int]
    alerts_by_analyzer: Dict[str, int]
    alerts_by_source_ip: Dict[str, int]
    alerts_by_target_ip: Dict[str, int]
    time_range_hours: int
    start_time: datetime
    end_time: datetime

    model_config = ConfigDict(from_attributes=True)
