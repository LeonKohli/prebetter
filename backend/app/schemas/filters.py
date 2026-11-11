"""Query-parameter models of the alert, group and timeline routes."""

import ipaddress
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.core.datetime_utils import ensure_timezone

SEVERITY_LABELS = ("high", "medium", "low", "info")


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class AlertSort(str, Enum):
    DETECT_TIME = "detect_time"
    SEVERITY = "severity"
    CLASSIFICATION = "classification"
    SOURCE_IP = "source_ip"
    TARGET_IP = "target_ip"
    ANALYZER = "analyzer"


class GroupSort(str, Enum):
    TOTAL_COUNT = "total_count"
    DETECT_TIME = "detect_time"
    SOURCE_IP = "source_ip"
    TARGET_IP = "target_ip"


class TimeFrame(str, Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


def csv(value: str | None) -> list[str]:
    """Split a comma-separated query parameter; empty items are dropped."""
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def parse_ip_filter(value: str) -> str:
    """
    Normalize an address, CIDR network or partial IPv4 prefix for a `term` query on an
    `ip` field. A prefix of one to three octets stands for /8, /16 or /24
    ("10.128" is 10.128.0.0/16).

    Raises ValueError for anything else.
    """
    value = value.strip()
    octets = value.split(".")
    if len(octets) < 4 and all(octet.isdecimal() for octet in octets):
        padded = ".".join(octets + ["0"] * (4 - len(octets)))
        return str(ipaddress.ip_network(f"{padded}/{8 * len(octets)}"))
    if "/" in value:
        return str(ipaddress.ip_network(value, strict=False))
    return str(ipaddress.ip_address(value))


class AlertFilterParams(BaseModel):
    """Filters common to the alert list, the groups and the timeline."""

    severity: str | None = Field(
        None,
        description="Comma-separated severity labels: high, medium, low, info",
        examples=["high", "high,medium"],
    )
    classification: str | None = Field(
        None,
        description="Comma-separated exact classification (rule) names",
    )
    start_date: datetime | None = Field(
        None, description="Alerts detected on or after this datetime (UTC)"
    )
    end_date: datetime | None = Field(
        None, description="Alerts detected on or before this datetime (UTC)"
    )
    source_ip: str | None = Field(
        None,
        description="Address, CIDR network or partial IPv4 prefix",
        examples=["192.0.2.10", "192.0", "198.51.100.0/24", "2001:db8::/32"],
    )
    target_ip: str | None = Field(
        None,
        description="Address, CIDR network or partial IPv4 prefix",
        examples=["192.0.2.10", "192.0", "198.51.100.0/24", "2001:db8::/32"],
    )
    server: str | None = Field(
        None, description="Comma-separated sensor names", examples=["s01,s02"]
    )
    require_ips: bool = Field(
        True, description="Only include alerts with both a source and a target address"
    )

    @field_validator("start_date", "end_date")
    @classmethod
    def utc_if_naive(cls, v: datetime | None) -> datetime | None:
        return ensure_timezone(v) if v else None

    @field_validator("severity")
    @classmethod
    def known_severities(cls, v: str | None) -> str | None:
        unknown = [label for label in csv(v) if label not in SEVERITY_LABELS]
        if unknown:
            raise ValueError(
                f"Unknown severity {unknown}; expected {', '.join(SEVERITY_LABELS)}"
            )
        return v

    @field_validator("source_ip", "target_ip")
    @classmethod
    def normalized_ip_filter(cls, v: str | None) -> str | None:
        return parse_ip_filter(v) if v else None


class PaginationParams(BaseModel):
    """Page selection (max 100 items per page)."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    size: int = Field(100, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    def total_pages(self, total: int) -> int:
        return -(-total // self.size)


# Each route takes exactly one of these as `Annotated[..., Query()]`: FastAPI validates a
# query model as a whole (422 on failure) but cannot mix it with other query parameters.
class AlertListParams(AlertFilterParams, PaginationParams):
    sort_by: AlertSort = AlertSort.DETECT_TIME
    sort_order: SortOrder = SortOrder.DESC


class GroupListParams(AlertFilterParams, PaginationParams):
    sort_by: GroupSort = GroupSort.TOTAL_COUNT
    sort_order: SortOrder = SortOrder.DESC


class TimelineParams(AlertFilterParams):
    time_frame: TimeFrame = TimeFrame.HOUR
