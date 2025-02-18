from datetime import datetime, UTC, timedelta
from typing import Optional

def ensure_timezone(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensures a datetime object has timezone information (UTC).
    If the datetime is naive (has no timezone), UTC is assumed.
    
    Args:
        dt: The datetime object to check
        
    Returns:
        The datetime object with UTC timezone if it was naive,
        or the original datetime if it already had timezone information.
        Returns None if input is None.
    """
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

def get_current_time() -> datetime:
    """
    Returns the current time with UTC timezone.
    This is the preferred way to get the current time in the application.
    
    Returns:
        Current time as a timezone-aware datetime object (UTC)
    """
    return datetime.now(UTC)

def format_datetime(dt: Optional[datetime], include_timezone: bool = True) -> str:
    """
    Formats a datetime object consistently throughout the application.
    
    Args:
        dt: The datetime object to format
        include_timezone: Whether to include timezone in the output string
        
    Returns:
        Formatted datetime string, or empty string if input is None
    """
    if dt is None:
        return ""
    dt = ensure_timezone(dt)
    format_string = "%d %b %Y, %H:%M:%S"
    if include_timezone:
        format_string += " %Z"
    return dt.strftime(format_string)

def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Parses a datetime string into a timezone-aware datetime object.
    Assumes UTC if no timezone information is present in the string.
    
    Args:
        dt_str: The datetime string to parse
        
    Returns:
        Timezone-aware datetime object, or None if input is None/invalid
    """
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return ensure_timezone(dt)
    except ValueError:
        return None

def get_time_range(hours: int) -> tuple[datetime, datetime]:
    """
    Gets a time range from now going back specified number of hours.
    Useful for queries that need a time window.
    
    Args:
        hours: Number of hours to look back
        
    Returns:
        Tuple of (start_time, end_time) as timezone-aware datetime objects
    """
    end_time = get_current_time()
    start_time = end_time - timedelta(hours=hours)
    return start_time, end_time 