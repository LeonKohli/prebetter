from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AnalyzerBasicInfo(BaseModel):
    name: str
    host: Optional[str]

    class Config:
        from_attributes = True

class AlertListItem(BaseModel):
    alert_id: int
    detect_time: datetime
    classification_text: str
    severity: Optional[str]
    source_ipv4: Optional[str]
    target_ipv4: Optional[str]
    analyzer: Optional[AnalyzerBasicInfo]

    class Config:
        from_attributes = True

class AlertListResponse(BaseModel):
    total: int
    items: List[AlertListItem]
    page: int
    size: int

# Detailed view schemas
class ReferenceInfo(BaseModel):
    origin: str
    name: str
    url: str

    class Config:
        from_attributes = True

class ServiceInfo(BaseModel):
    port: Optional[int]
    protocol: str
    direction: str

    class Config:
        from_attributes = True

class AdditionalInfo(BaseModel):
    snort_rule_sid: Optional[int]
    snort_rule_rev: Optional[int]
    ip_version: Optional[int]
    payload_preview: Optional[str]

    class Config:
        from_attributes = True

class AnalyzerDetailInfo(BaseModel):
    name: str
    host: Optional[str]
    analyzer_id: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    version: Optional[str]
    class_type: Optional[str]
    ostype: Optional[str]
    osversion: Optional[str]

    class Config:
        from_attributes = True

class AlertDetail(BaseModel):
    alert_id: int
    detect_time: datetime
    detect_time_usec: int
    detect_time_gmtoff: int
    classification_text: str
    classification_ident: Optional[str]
    severity: Optional[str]
    source_ipv4: Optional[str]
    target_ipv4: Optional[str]
    analyzer: Optional[AnalyzerDetailInfo]
    description: Optional[str]
    completion: Optional[str]
    impact_type: Optional[str]
    references: List[ReferenceInfo] = []
    services: List[ServiceInfo] = []
    additional_data: Optional[AdditionalInfo]

    class Config:
        from_attributes = True 