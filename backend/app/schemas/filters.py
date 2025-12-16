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

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.core.datetime_utils import ensure_timezone


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
        description="Filter by source IPv4 address (exact match)",
        examples=["192.168.1.100"],
    )
    target_ip: Optional[str] = Field(
        None,
        description="Filter by target IPv4 address (exact match)",
        examples=["10.0.0.1"],
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

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def ensure_tz(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure timezone-aware datetimes."""
        if v is None:
            return None
        return ensure_timezone(v)

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
    Pagination parameters for list endpoints.

    Usage:
        pagination: Annotated[PaginationParams, Depends()]
    """

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    size: int = Field(100, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for SQL queries."""
        return (self.page - 1) * self.size

    def total_pages(self, total: int) -> int:
        """Calculate total pages for a given total count."""
        return calculate_total_pages(total, self.size)


class TimelineFilterParams(AlertFilterParams):
    """
    Filter parameters specific to timeline queries.

    Extends AlertFilterParams with timeline-specific fields.
    """

    time_frame: str = Field(
        "hour",
        description="Grouping interval: hour, day, week, month",
        examples=["hour", "day", "week", "month"],
    )

    @field_validator("time_frame")
    @classmethod
    def validate_time_frame(cls, v: str) -> str:
        """Validate time_frame is one of allowed values."""
        allowed = {"hour", "day", "week", "month"}
        if v not in allowed:
            raise ValueError(f"time_frame must be one of: {', '.join(allowed)}")
        return v
