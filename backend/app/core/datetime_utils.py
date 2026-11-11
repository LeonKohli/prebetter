from datetime import datetime, UTC


def ensure_timezone(dt: datetime) -> datetime:
    """Return dt unchanged if it is timezone-aware, otherwise interpret it as UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def get_current_time() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)
