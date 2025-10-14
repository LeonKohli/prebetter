"""
Model conversion utilities for the Prelude IDS API.

These utilities handle the conversion between database result objects and
API schema models, providing consistent transformation logic across the application.
"""

from typing import Optional, List, Any, Dict, Union
import base64
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
    """Convert a SQLAlchemy result row to AlertListItem schema."""
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

    create_time_info = None
    if result.create_time:
        # Timestamp already converted to local time in SQL query
        create_time_info = TimeInfo(timestamp=result.create_time)

    # Timestamp already converted to local time in SQL query
    detect_time_info = TimeInfo(timestamp=result.detect_time)

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
    """Convert a pair result and its associated alerts to a GroupedAlert schema."""
    key = (pair.source_ipv4, pair.target_ipv4)
    alerts = alerts_map.get(key, [])

    # Use the group's overall latest_time for all alerts for consistency
    # The backend query should handle timezone conversion using TIMESTAMPADD
    if hasattr(pair, "latest_time") and pair.latest_time:
        for alert in alerts:
            alert.detected_at = pair.latest_time

    return GroupedAlert(
        source_ipv4=pair.source_ipv4,
        target_ipv4=pair.target_ipv4,
        total_count=pair.total_count,
        alerts=alerts,
    )


def process_grouped_alerts_details(alerts, max_limit=None):
    """Process alert results into a grouped alerts map.

    Args:
        alerts: Query results containing alert classification data
        max_limit: Optional maximum number of classifications to process (None = unlimited)
                   Note: Real-world data shows ~1600 total classifications across all pairs,
                   so this limit is generally unnecessary and was removed by default.
    """
    alerts_map = {}
    processed_count = 0

    for a in alerts:
        # Stop processing if we've reached the limit (only if limit is set)
        if max_limit is not None and processed_count >= max_limit:
            break

        key = (a.source_ipv4, a.target_ipv4)
        if key not in alerts_map:
            alerts_map[key] = []

        if a.classification:
            analyzer_hosts = []
            if a.analyzer_hosts:
                for host in a.analyzer_hosts.split(","):
                    if host:
                        parts = host.split(".")
                        analyzer_hosts.append(parts[0] if parts else None)

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
            processed_count += 1

    # Sort alerts within each group by detected_at time (newest first)
    for key in alerts_map:
        alerts_map[key].sort(
            key=lambda x: x.detected_at if x.detected_at else "", reverse=True
        )

    return alerts_map


def build_analyzer_info(
    analyzer_data: Union[Row, Any],
    node_info: Optional[NodeInfo] = None,
    process_info: Optional[ProcessInfo] = None,
    analyzer_time_info: Optional[AnalyzerTimeInfo] = None,
    chain_index: Optional[int] = None,
) -> AnalyzerInfo:
    """Build an AnalyzerInfo schema from analyzer-related fields."""
    # -1 = Primary, Concentrator class = aggregation point, others = secondary
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
    """Build a NodeInfo schema from node-related fields."""
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
    """Build a ProcessInfo schema from process-related fields."""
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
    """Remove b'...' or b"..." representation from a string."""
    if value is None:
        return None

    cleaned_value = value
    if isinstance(value, str):
        if value.startswith("b'") and value.endswith("'"):
            cleaned_value = value[2:-1]
        elif value.startswith('b"') and value.endswith('"'):
            cleaned_value = value[2:-1]

    return cleaned_value


def process_additional_data(add_data_rows):
    """Process AdditionalData rows into a dictionary with type conversion.

    Changes:
    - For values with type == "byte-string", return exactly two representations:
        { "readable": <utf-8 decoded with replacement>,
          "original": <base64 string> }
      This preserves the original bytes (JSON-safe base64) and a readable form — no extra fields.
    - Always return full payloads (no truncation controlled by query params).
    """
    additional_data = {}
    if not add_data_rows:
        return additional_data

    for row in add_data_rows:
        meaning = getattr(row, "meaning", None)
        raw_data = getattr(row, "data", None)
        data_type = getattr(row, "type", None)

        if meaning is None:
            continue

        current_value = None

        try:
            if data_type == "byte-string":
                if isinstance(raw_data, bytes):
                    # Preserve original bytes (base64) and a readable text view
                    try:
                        b64 = base64.b64encode(raw_data).decode("ascii")
                    except Exception:
                        b64 = ""
                    text_value = raw_data.decode("utf-8", errors="replace")
                    current_value = {"readable": text_value, "original": b64}
                elif isinstance(raw_data, str):
                    # We only have a string; provide readable text and no raw
                    current_value = {
                        "readable": clean_byte_string(raw_data),
                        "original": None,
                    }
                else:
                    # Fallback to string representation
                    current_value = {"readable": str(raw_data), "original": None}

            else:
                str_value = str(raw_data)
                cleaned_str = clean_byte_string(str_value)

                if data_type == "integer":
                    try:
                        current_value = (
                            int(cleaned_str) if cleaned_str is not None else None
                        )
                    except (ValueError, TypeError):
                        current_value = cleaned_str
                elif data_type == "float" or data_type == "real":
                    try:
                        current_value = (
                            float(cleaned_str) if cleaned_str is not None else None
                        )
                    except (ValueError, TypeError):
                        current_value = cleaned_str
                elif data_type == "boolean":
                    if cleaned_str is not None:
                        if cleaned_str.lower() == "true":
                            current_value = True
                        elif cleaned_str.lower() == "false":
                            current_value = False
                        else:
                            current_value = cleaned_str
                    else:
                        current_value = None
                else:
                    current_value = cleaned_str

            additional_data[meaning] = current_value

        except Exception as e:
            additional_data[meaning] = f"Error processing data: {str(e)}"
            # TODO: Add logging when logger is available

    return additional_data


def format_relative_time(last_hb_time, current_time):
    """Format a heartbeat timestamp into a relative time string."""
    if last_hb_time is None:
        return "never"

    current_time = ensure_timezone(current_time)
    last_hb_time = ensure_timezone(last_hb_time)

    if current_time is None or last_hb_time is None:
        return "unknown"

    if last_hb_time > current_time:
        return "in the future"

    delta = current_time - last_hb_time
    seconds = int(delta.total_seconds())
    days = delta.days

    if days >= 365:
        years = days // 365
        return f"{years} year{'' if years == 1 else 's'} ago"
    if days >= 30:
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
    """Determine heartbeat status based on last timestamp and interval."""
    if last_hb_time is None:
        return "unknown"

    current_time = ensure_timezone(current_time)
    last_hb_time = ensure_timezone(last_hb_time)

    if current_time is None or last_hb_time is None:
        return "unknown"

    if last_hb_time > current_time:
        # Future timestamps indicate clock sync issues
        return "active"

    delta_seconds = (current_time - last_hb_time).total_seconds()
    offline_threshold = interval * 2

    if delta_seconds <= interval:
        return "active"
    elif delta_seconds <= offline_threshold:
        return "inactive"
    else:
        return "offline"
