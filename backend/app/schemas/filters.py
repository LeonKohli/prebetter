"""
Filter schemas for FastAPI endpoints.

These Pydantic models serve as SINGLE SOURCE OF TRUTH for all filter parameters,
eliminating scattered Optional[str] params across routes.

Usage with MULTIPLE Pydantic models as query params:
    from typing import Annotated
    from fastapi import Depends

    @router.get("/alerts")
    async def list_alerts(
        filters: Annotated[AlertFilterParams, Depends()],
        pagination: Annotated[PaginationParams, Depends()],
    ):
        ...

Note: Use Depends() (not Query()) when you have MULTIPLE Pydantic models.
Query() is for a SINGLE model capturing ALL query params.
"""

import ipaddress
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.core.datetime_utils import ensure_timezone


@dataclass(frozen=True, slots=True)
class IPRange:
    """
    Parsed IP filter - either a single address or a network range.

    Attributes:
        network_int: Network address as integer (for CIDR) or IP as integer (for single)
        broadcast_int: Broadcast address as integer (for CIDR) or same as network_int (for single)
        is_cidr: True if this represents a network range, False for single IP
        original: Original input string for exact matching fallback
        expanded: Human-readable expanded form (e.g., "10.128.9.0 - 10.128.9.255")
    """

    network_int: int
    broadcast_int: int
    is_cidr: bool
    original: str
    expanded: str


def _is_valid_octet(s: str) -> bool:
    """Check if string is a valid IPv4 octet (0-255)."""
    if not s or not s.isdigit():
        return False
    val = int(s)
    return 0 <= val <= 255


def _expand_partial_ip(segments: list[str]) -> tuple[str, str]:
    """
    Expand partial IP segments to full min/max range.

    Examples:
        ["10"] -> ("10.0.0.0", "10.255.255.255")
        ["10", "128"] -> ("10.128.0.0", "10.128.255.255")
        ["10", "128", "9"] -> ("10.128.9.0", "10.128.9.255")
    """
    min_segments = segments + ["0"] * (4 - len(segments))
    max_segments = segments + ["255"] * (4 - len(segments))
    return ".".join(min_segments), ".".join(max_segments)


def parse_ip_filter(value: str) -> IPRange:
    """
    Parse an IP filter value into an IPRange.

    Supports:
        - Single IPv4 address: "192.168.1.100"
        - CIDR notation: "192.168.1.0/24"
        - Partial IP (auto-expanded): "10.128.9" -> matches 10.128.9.0-10.128.9.255

    Raises:
        ValueError: If the input is not a valid IPv4 address, CIDR, or partial IP
    """
    value = value.strip()

    if "/" in value:
        try:
            network = ipaddress.IPv4Network(value, strict=False)
            return IPRange(
                network_int=int(network.network_address),
                broadcast_int=int(network.broadcast_address),
                is_cidr=True,
                original=value,
                expanded=f"{network.network_address} - {network.broadcast_address}",
            )
        except (
            ipaddress.AddressValueError,
            ipaddress.NetmaskValueError,
            ValueError,
        ) as e:
            raise ValueError(f"Invalid CIDR notation: {value}") from e

    segments = value.split(".")

    if (
        len(segments) < 4
        and all(_is_valid_octet(s) for s in segments)
        and len(segments) >= 1
    ):
        min_ip, max_ip = _expand_partial_ip(segments)
        min_addr = ipaddress.IPv4Address(min_ip)
        max_addr = ipaddress.IPv4Address(max_ip)
        return IPRange(
            network_int=int(min_addr),
            broadcast_int=int(max_addr),
            is_cidr=True,
            original=value,
            expanded=f"{min_ip} - {max_ip}",
        )

    try:
        addr = ipaddress.IPv4Address(value)
        addr_int = int(addr)
        return IPRange(
            network_int=addr_int,
            broadcast_int=addr_int,
            is_cidr=False,
            original=value,
            expanded=value,
        )
    except ipaddress.AddressValueError as e:
        raise ValueError(f"Invalid IPv4 address: {value}") from e


def calculate_total_pages(total: int, page_size: int) -> int:
    """Calculate total pages - use this instead of inline math."""
    return (total + page_size - 1) // page_size


class AlertFilterParams(BaseModel):
    """
    Common filter parameters for alert queries.

    Use as FastAPI dependency for consistent filtering across endpoints:
        filters: Annotated[AlertFilterParams, Depends()]

    Supports comma-separated values for: severity, classification, server
    """

    severity: Optional[str] = Field(
        None,
        description="Filter by severity level(s). Comma-separated for multiple: 'high,medium'",
        examples=["high", "high,medium,low"],
    )
    classification: Optional[str] = Field(
        None,
        description="Filter by classification text(s). Comma-separated for multiple",
        examples=["Misc Attack", "Attempted Information Leak,Misc Attack"],
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Filter alerts detected on or after this datetime (UTC)",
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Filter alerts detected on or before this datetime (UTC)",
    )
    source_ip: Optional[str] = Field(
        None,
        description="Filter by source IP. Accepts: full IP (192.168.1.100), partial IP (10.128.9), or CIDR (10.0.0.0/8)",
        examples=["192.168.1.100", "10.128.9", "10.0.0.0/8"],
    )
    target_ip: Optional[str] = Field(
        None,
        description="Filter by target IP. Accepts: full IP (10.0.0.1), partial IP (192.168), or CIDR (192.168.0.0/16)",
        examples=["10.0.0.1", "192.168", "192.168.0.0/16"],
    )
    server: Optional[str] = Field(
        None,
        description="Filter by server/node name (short name prefix). Comma-separated for multiple",
        examples=["server-001", "server-001,server-002"],
    )
    analyzer_name: Optional[str] = Field(
        None,
        description="Filter by analyzer name",
        examples=["snort"],
    )
    require_ips: bool = Field(
        True,
        description="Only include alerts with both source AND target IPv4 addresses. "
        "Alerts without IPs are typically not useful for security analysis.",
    )

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def ensure_tz(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure timezone-aware datetimes."""
        if v is None:
            return None
        return ensure_timezone(v)

    @field_validator("source_ip", "target_ip", mode="after")
    @classmethod
    def validate_ip_filter(cls, v: Optional[str]) -> Optional[str]:
        """Validate IP filter is a valid IPv4 address or CIDR notation."""
        if v is None:
            return None
        parse_ip_filter(v)
        return v

    def source_ip_range(self) -> Optional[IPRange]:
        """Parse source_ip into IPRange for query building."""
        if not self.source_ip:
            return None
        return parse_ip_filter(self.source_ip)

    def target_ip_range(self) -> Optional[IPRange]:
        """Parse target_ip into IPRange for query building."""
        if not self.target_ip:
            return None
        return parse_ip_filter(self.target_ip)

    def severity_list(self) -> list[str]:
        """Parse severity into list for IN queries."""
        if not self.severity:
            return []
        return [s.strip() for s in self.severity.split(",") if s.strip()]

    def classification_list(self) -> list[str]:
        """Parse classification into list for IN queries."""
        if not self.classification:
            return []
        return [c.strip() for c in self.classification.split(",") if c.strip()]

    def server_list(self) -> list[str]:
        """Parse server into list for IN queries."""
        if not self.server:
            return []
        return [s.strip() for s in self.server.split(",") if s.strip()]


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints (max 100 items).

    Usage:
        pagination: Annotated[PaginationParams, Depends()]
    """

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    size: int = Field(100, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        """Calculate offset for SQL queries."""
        return (self.page - 1) * self.size

    def total_pages(self, total: int) -> int:
        """Calculate total pages for a given total count."""
        return calculate_total_pages(total, self.size)
