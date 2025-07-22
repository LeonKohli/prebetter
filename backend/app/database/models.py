"""
Model conversion utilities for the Prelude SIEM API.

These utilities handle the conversion between database result objects and
API schema models, providing consistent transformation logic across the application.
"""

from typing import Optional, List, Any, Dict, Union
from sqlalchemy.engine.row import Row

from ..schemas.prelude import (
    AlertListItem,
    TimeInfo,
    AnalyzerInfo,
    NodeInfo,
    GroupedAlert,
    GroupedAlertDetail,
    ProcessInfo,
    AnalyzerTimeInfo,
)
from app.core.datetime_utils import ensure_timezone


def alert_result_to_list_item(result: Row) -> AlertListItem:
    """
    Convert a SQLAlchemy result row to AlertListItem schema.

    Args:
        result: SQLAlchemy result row containing alert data with joined analyzer and node info

    Returns:
        AlertListItem: Pydantic model with formatted alert data
    """
    node_info = None
    if (
        result.analyzer_host
        or getattr(result, "node_location", None)
        or getattr(result, "node_category", None)
    ):
        node_info = NodeInfo(
            name=result.analyzer_host,
            location=getattr(result, "node_location", None),
            category=getattr(result, "node_category", None),
        )

    analyzer_info = None
    if result.analyzer_name:
        analyzer_info = AnalyzerInfo(
            name=f"{result.analyzer_name} ({result.analyzer_host.split('.')[0]})"
            if result.analyzer_host
            else result.analyzer_name,
            node=node_info,
            model=result.analyzer_model,
            manufacturer=getattr(result, "analyzer_manufacturer", None),
            version=getattr(result, "analyzer_version", None),
            class_type=getattr(result, "analyzer_class", None),
            ostype=getattr(result, "analyzer_ostype", None),
            osversion=getattr(result, "analyzer_osversion", None),
        )

    # Handle create_time with optional usec and gmtoff
    create_time_info = None
    if result.create_time:
        create_time_info = TimeInfo(
            timestamp=result.create_time,
            usec=result.create_time_usec
            if hasattr(result, "create_time_usec")
            else None,
            gmtoff=result.create_time_gmtoff
            if hasattr(result, "create_time_gmtoff")
            else None,
        )

    # Handle detect_time with optional usec and gmtoff
    detect_time_info = TimeInfo(
        timestamp=result.detect_time,
        usec=result.detect_time_usec if hasattr(result, "detect_time_usec") else None,
        gmtoff=result.detect_time_gmtoff
        if hasattr(result, "detect_time_gmtoff")
        else None,
    )

    alert_item = AlertListItem(
        id=str(result._ident),
        message_id=result.messageid,
        created_at=create_time_info,
        detected_at=detect_time_info,
        classification_text=result.classification_text,
        severity=result.severity,
        source_ipv4=result.source_ipv4,
        target_ipv4=result.target_ipv4,
        analyzer=analyzer_info,
    )
    return alert_item


def grouped_alert_to_response(
    pair: Row, alerts_map: Dict[tuple, List[GroupedAlertDetail]]
) -> GroupedAlert:
    """
    Convert a pair result and its associated alerts to a GroupedAlert schema.

    Args:
        pair: SQLAlchemy result row containing the source/target pair with counts
        alerts_map: Dictionary mapping (source_ipv4, target_ipv4) to a list of GroupedAlertDetail

    Returns:
        GroupedAlert: Pydantic model with formatted grouped alert data
    """
    key = (pair.source_ipv4, pair.target_ipv4)
    return GroupedAlert(
        source_ipv4=pair.source_ipv4,
        target_ipv4=pair.target_ipv4,
        total_count=pair.total_count,
        alerts=alerts_map.get(key, []),
    )


def process_grouped_alerts_details(alerts):
    """
    Process alert results into a grouped alerts map.

    Args:
        alerts: List of SQLAlchemy result rows with grouped alert details

    Returns:
        Dict mapping (source_ipv4, target_ipv4) to a list of GroupedAlertDetail
    """
    # Use a dict comprehension for better performance
    alerts_map = {}

    # Create a map of alerts for each source-target pair
    for a in alerts:
        key = (a.source_ipv4, a.target_ipv4)
        if key not in alerts_map:
            alerts_map[key] = []

        if a.classification:  # Only add if classification is not None
            # Process analyzer hosts efficiently
            analyzer_hosts = []
            if a.analyzer_hosts:
                for host in a.analyzer_hosts.split(","):
                    if host:
                        # Just take the first part of the hostname
                        parts = host.split(".")
                        analyzer_hosts.append(parts[0] if parts else None)

            # Process analyzers efficiently
            analyzers = []
            if a.analyzers:
                analyzers = [ana for ana in a.analyzers.split(",") if ana]

            alerts_map[key].append(
                GroupedAlertDetail(
                    classification=a.classification,
                    count=a.count,
                    analyzer=analyzers,
                    analyzer_host=analyzer_hosts,
                    detected_at=a.latest_time,
                )
            )

    return alerts_map


def build_analyzer_info(
    analyzer_data: Union[Row, Any],
    node_info: Optional[NodeInfo] = None,
    process_info: Optional[ProcessInfo] = None,
    analyzer_time_info: Optional[AnalyzerTimeInfo] = None,
    chain_index: Optional[int] = None,
) -> AnalyzerInfo:
    """
    Build an AnalyzerInfo schema from analyzer-related fields.

    Args:
        analyzer_data: SQLAlchemy result row or object containing analyzer data
        node_info: Optional NodeInfo model
        process_info: Optional process information
        analyzer_time_info: Optional analyzer time information
        chain_index: Optional chain index value

    Returns:
        AnalyzerInfo: Pydantic model with formatted analyzer data
    """
    # Determine analyzer role based on class and position
    role = None
    index = (
        chain_index
        if chain_index is not None
        else getattr(analyzer_data, "_index", None)
    )

    if index is not None:
        if index == -1:
            role = "Primary"
        elif getattr(analyzer_data, "class", "") == "Concentrator":
            role = "Concentrator"
        else:
            role = "Secondary"

    return AnalyzerInfo(
        name=analyzer_data.name,
        analyzer_id=getattr(analyzer_data, "analyzerid", None),
        node=node_info,
        model=getattr(analyzer_data, "model", None),
        manufacturer=getattr(analyzer_data, "manufacturer", None),
        version=getattr(analyzer_data, "version", None),
        class_type=getattr(analyzer_data, "class", None),
        ostype=getattr(analyzer_data, "ostype", None),
        osversion=getattr(analyzer_data, "osversion", None),
        process=process_info,
        analyzer_time=analyzer_time_info,
        chain_index=index,
        role=role,
    )


def build_node_info(node_data: Union[Row, Any]) -> Optional[NodeInfo]:
    """
    Build a NodeInfo schema from node-related fields.

    Args:
        node_data: SQLAlchemy result row or object containing node data

    Returns:
        NodeInfo: Pydantic model with formatted node data or None if no data
    """
    if not node_data:
        return None

    return NodeInfo(
        name=getattr(node_data, "name", None),
        location=getattr(node_data, "location", None),
        category=getattr(node_data, "category", None),
        ident=getattr(node_data, "ident", None),
    )


def build_process_info(
    process_data: Union[Row, Any], process_args=None, process_env=None
) -> Optional[ProcessInfo]:
    """
    Build a ProcessInfo schema from process-related fields.

    Args:
        process_data: SQLAlchemy result row or object containing process data
        process_args: Optional list of process arguments
        process_env: Optional list of process environment variables

    Returns:
        ProcessInfo: Pydantic model with formatted process data or None if no data
    """
    if not process_data:
        return None

    args = []
    if process_args:
        args = [arg[0] for arg in process_args]

    env = []
    if process_env:
        env = [env_var[0] for env_var in process_env]

    return ProcessInfo(
        name=process_data.name,
        pid=process_data.pid,
        path=process_data.path,
        args=args,
        env=env,
    )


def clean_byte_string(value: Optional[str]) -> Optional[str]:
    """
    Removes b'...' or b"..." representation from a string.
    Does NOT perform type conversion.

    Args:
        value: The string value, potentially with a byte string prefix

    Returns:
        Cleaned string value or None if input is None
    """
    if value is None:
        return None

    cleaned_value = value
    # Remove b'...' or b"..." if present
    if isinstance(value, str):
        if value.startswith("b'") and value.endswith("'"):
            cleaned_value = value[2:-1]
        elif value.startswith('b"') and value.endswith('"'):
            cleaned_value = value[2:-1]

    return cleaned_value


def process_additional_data(add_data_rows, truncate_payload=False):
    """
    Process AdditionalData rows into a dictionary with type conversion.

    Args:
        add_data_rows: SQLAlchemy query results containing AdditionalData rows
        truncate_payload: Whether to truncate payload data to 100 characters

    Returns:
        Dict mapping meaning to cleaned and typed data value
    """
    additional_data = {}
    if not add_data_rows:
        return additional_data

    for row in add_data_rows:
        # Use getattr for safety in case attributes are missing
        meaning = getattr(row, "meaning", None)
        raw_data = getattr(row, "data", None)
        data_type = getattr(row, "type", None)

        if meaning is None:
            continue  # Skip rows without a meaning

        current_value = None

        try:
            # 1. Handle byte-string first (as it might be actual bytes)
            if data_type == "byte-string":
                if isinstance(raw_data, bytes):
                    # Decode actual bytes
                    decoded_str = raw_data.decode("utf-8", errors="ignore")
                    # Use lower() for case-insensitive check
                    if (
                        meaning.lower() == "payload"
                        and truncate_payload
                        and len(decoded_str) > 100
                    ):
                        current_value = decoded_str[:100] + "... (truncated)"
                    else:
                        # Even decoded bytes might represent b'...', clean them
                        current_value = clean_byte_string(decoded_str)
                elif isinstance(raw_data, str):
                    # Handle strings that look like byte strings
                    current_value = clean_byte_string(raw_data)
                else:
                    current_value = str(raw_data)  # Fallback

            # 2. Handle other types (convert raw_data to string first)
            else:
                str_value = str(raw_data)
                cleaned_str = clean_byte_string(str_value)  # Clean potential b'...'

                if data_type == "integer":
                    try:
                        current_value = (
                            int(cleaned_str) if cleaned_str is not None else None
                        )
                    except (ValueError, TypeError):
                        current_value = cleaned_str  # Keep original on error
                elif data_type == "float" or data_type == "real":
                    try:
                        current_value = (
                            float(cleaned_str) if cleaned_str is not None else None
                        )
                    except (ValueError, TypeError):
                        current_value = cleaned_str  # Keep original on error
                elif data_type == "boolean":
                    if cleaned_str is not None:
                        if cleaned_str.lower() == "true":
                            current_value = True
                        elif cleaned_str.lower() == "false":
                            current_value = False
                        else:
                            current_value = cleaned_str  # Keep original on error
                    else:
                        current_value = None
                # Includes type == "string" and any other unknown types
                else:
                    current_value = cleaned_str

            additional_data[meaning] = current_value

        except Exception as e:
            # Broad exception catch for safety during processing
            additional_data[meaning] = f"Error processing data: {str(e)}"
            # Optionally log the error: logger.error(f"Error processing additional data for {meaning}: {e}")

    return additional_data


def format_relative_time(last_hb_time, current_time):
    """
    Format a heartbeat timestamp into a relative time string.
    Handles None input and future times.
    """
    if last_hb_time is None:
        return "never"

    # Ensure times are timezone-aware (assume UTC if naive)
    current_time = ensure_timezone(current_time)
    last_hb_time = ensure_timezone(last_hb_time)

    if current_time is None or last_hb_time is None:
        return "unknown"

    if last_hb_time > current_time:
        return "in the future"

    delta = current_time - last_hb_time
    seconds = int(delta.total_seconds())
    days = delta.days

    # Order matters: check years, then months, then weeks, etc.
    if days >= 365:
        years = days // 365
        return f"{years} year{'' if years == 1 else 's'} ago"
    # Check months *before* years for correct calculation (e.g., 364 days)
    if days >= 30:
        # Use a more accurate average month length or a simpler division
        # Simple division by 30 is often acceptable for relative time
        months = days // 30
        return f"{months} month{'' if months == 1 else 's'} ago"
    if days >= 7:
        weeks = days // 7
        return f"{weeks} week{'' if weeks == 1 else 's'} ago"
    if days >= 1:
        return f"{days} day{'' if days == 1 else 's'} ago"
    if seconds >= 3600:
        hours = seconds // 3600
        return f"{hours} hour{'' if hours == 1 else 's'} ago"
    if seconds >= 60:
        minutes = seconds // 60
        return f"{minutes} minute{'' if minutes == 1 else 's'} ago"
    return f"{seconds} second{'' if seconds == 1 else 's'} ago"


def determine_heartbeat_status(last_hb_time, current_time, interval=600):
    """
    Determine if a heartbeat is active, inactive, or offline based on its last timestamp.

    Args:
        last_hb_time: The heartbeat timestamp (datetime or None)
        current_time: The current time (datetime)
        interval: Heartbeat interval in seconds (default: 600)

    Returns:
        String "active", "inactive", "offline", or "unknown"
    """
    if last_hb_time is None:
        return "unknown"

    # Ensure times are timezone-aware (assume UTC if naive)
    current_time = ensure_timezone(current_time)
    last_hb_time = ensure_timezone(last_hb_time)

    if current_time is None or last_hb_time is None:
        return "unknown"

    if last_hb_time > current_time:
        # Treat future heartbeats as active for status purposes
        return "active"

    delta_seconds = (current_time - last_hb_time).total_seconds()
    offline_threshold = interval * 2

    if delta_seconds <= interval:
        return "active"
    elif delta_seconds <= offline_threshold:
        return "inactive"
    else:
        return "offline"
