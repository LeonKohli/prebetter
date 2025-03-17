"""
Model conversion utilities for the Prelude SIEM API.

These utilities handle the conversion between database result objects and
API schema models, providing consistent transformation logic across the application.
"""

from typing import Optional, List, Any, Dict, Union
from datetime import timedelta
from sqlalchemy.engine.row import Row

from ..schemas.prelude import (
    AlertListItem, 
    TimeInfo, 
    AnalyzerInfo, 
    NodeInfo, 
    GroupedAlert, 
    GroupedAlertDetail,
    ProcessInfo,
    AnalyzerTimeInfo
)

def alert_result_to_list_item(result: Row) -> AlertListItem:
    """
    Convert a SQLAlchemy result row to AlertListItem schema.
    
    Args:
        result: SQLAlchemy result row containing alert data with joined analyzer and node info
        
    Returns:
        AlertListItem: Pydantic model with formatted alert data
    """
    node_info = None
    if result.analyzer_host or getattr(result, 'node_location', None) or getattr(result, 'node_category', None):
        node_info = NodeInfo(
            name=result.analyzer_host,
            location=getattr(result, 'node_location', None),
            category=getattr(result, 'node_category', None),
        )

    analyzer_info = None
    if result.analyzer_name:
        analyzer_info = AnalyzerInfo(
            name=f"{result.analyzer_name} ({result.analyzer_host.split('.')[0]})" if result.analyzer_host else result.analyzer_name,
            node=node_info,
            model=result.analyzer_model,
            manufacturer=getattr(result, 'analyzer_manufacturer', None),
            version=getattr(result, 'analyzer_version', None),
            class_type=getattr(result, 'analyzer_class', None),
            ostype=getattr(result, 'analyzer_ostype', None),
            osversion=getattr(result, 'analyzer_osversion', None),
        )

    alert_item = AlertListItem(
        alert_id=str(result._ident),
        message_id=result.messageid,
        create_time=TimeInfo(
            time=result.create_time,
            usec=getattr(result, 'create_time_usec', None),
            gmtoff=getattr(result, 'create_time_gmtoff', None),
        )
        if result.create_time
        else None,
        detect_time=TimeInfo(
            time=result.detect_time,
            usec=getattr(result, 'detect_time_usec', None),
            gmtoff=getattr(result, 'detect_time_gmtoff', None),
        ),
        classification_text=result.classification_text,
        severity=result.severity,
        source_ipv4=result.source_ipv4,
        target_ipv4=result.target_ipv4,
        analyzer=analyzer_info,
    )
    return alert_item

def grouped_alert_to_response(pair: Row, alerts_map: Dict[tuple, List[GroupedAlertDetail]]) -> GroupedAlert:
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
    
    # Set a reasonable limit to avoid processing too many alerts
    max_alerts = 1000
    
    # Create a map of alerts for each source-target pair
    for i, a in enumerate(alerts):
        # Exit early if we've processed enough alerts
        if i >= max_alerts:
            break
            
        key = (a.source_ipv4, a.target_ipv4)
        if key not in alerts_map:
            alerts_map[key] = []
            
        if a.classification:  # Only add if classification is not None
            # Process analyzer hosts efficiently
            analyzer_hosts = []
            if a.analyzer_hosts:
                for host in a.analyzer_hosts.split(','):
                    if host:
                        # Just take the first part of the hostname
                        parts = host.split('.')
                        analyzer_hosts.append(parts[0] if parts else None)
            
            # Process analyzers efficiently
            analyzers = []
            if a.analyzers:
                analyzers = [ana for ana in a.analyzers.split(',') if ana]
            
            alerts_map[key].append(
                GroupedAlertDetail(
                    classification=a.classification,
                    count=a.count,
                    analyzer=analyzers,
                    analyzer_host=analyzer_hosts,
                    time=a.latest_time,
                )
            )
    
    return alerts_map

def build_analyzer_info(
    analyzer_data: Union[Row, Any], 
    node_info: Optional[NodeInfo] = None,
    process_info: Optional[ProcessInfo] = None,
    analyzer_time_info: Optional[AnalyzerTimeInfo] = None,
    chain_index: Optional[int] = None
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
    index = chain_index if chain_index is not None else getattr(analyzer_data, '_index', None)
    
    if index is not None:
        if index == -1:
            role = "Primary"
        elif getattr(analyzer_data, "class", "") == "Concentrator":
            role = "Concentrator"
        else:
            role = "Secondary"

    return AnalyzerInfo(
        name=analyzer_data.name,
        analyzer_id=getattr(analyzer_data, 'analyzerid', None),
        node=node_info,
        model=getattr(analyzer_data, 'model', None),
        manufacturer=getattr(analyzer_data, 'manufacturer', None),
        version=getattr(analyzer_data, 'version', None),
        class_type=getattr(analyzer_data, 'class', None),
        ostype=getattr(analyzer_data, 'ostype', None),
        osversion=getattr(analyzer_data, 'osversion', None),
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
        name=getattr(node_data, 'name', None),
        location=getattr(node_data, 'location', None),
        category=getattr(node_data, 'category', None),
        ident=getattr(node_data, 'ident', None),
    )

def build_process_info(process_data: Union[Row, Any], process_args=None, process_env=None) -> Optional[ProcessInfo]:
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

def clean_byte_string(value: str) -> Optional[str]:
    """
    Process byte strings from AdditionalData by removing b'...' prefix and converting to proper type.
    
    Args:
        value: The string value, potentially with a byte string prefix
        
    Returns:
        Cleaned string value or None if input is None
    """
    if not value:
        return None
    # Remove b'...' if present
    if value.startswith("b'") and value.endswith("'"):
        value = value[2:-1]
    # Try to convert to int if it's numeric
    try:
        if value.isdigit():
            return str(int(value))
        return value
    except Exception:
        return value

def process_additional_data(add_data_rows, truncate_payload=False):
    """
    Process AdditionalData rows into a dictionary.
    
    Args:
        add_data_rows: SQLAlchemy query results containing AdditionalData rows
        truncate_payload: Whether to truncate payload data to 500 characters
        
    Returns:
        Dict mapping meaning to cleaned data value
    """
    additional_data = {}
    
    for row in add_data_rows:
        try:
            if row.type in ["integer", "real", "character"]:
                additional_data[row.meaning] = clean_byte_string(str(row.data))
            elif row.type == "byte-string":
                if row.meaning == "payload":
                    decoded = row.data.decode("utf-8", errors="ignore")
                    if truncate_payload and len(decoded) > 500:
                        decoded = decoded[:500] + "..."
                    additional_data[row.meaning] = decoded
                else:
                    additional_data[row.meaning] = clean_byte_string(
                        row.data.decode("utf-8", errors="ignore")
                    )
            else:
                additional_data[row.meaning] = str(row.data)
        except Exception as e:
            additional_data[row.meaning] = f"Error decoding data: {str(e)}"
    
    return additional_data

def format_relative_time(last_hb_time, current_time):
    """
    Format a heartbeat timestamp into a relative time string.
    
    Args:
        last_hb_time: The heartbeat timestamp
        current_time: The current time
        
    Returns:
        String describing the relative time (e.g., "5 minutes ago")
    """
    if last_hb_time:
        delta = current_time - last_hb_time
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds} seconds ago"
        elif seconds < 3600:
            return f"{seconds // 60} minutes ago"
        else:
            return f"{seconds // 3600} hours ago"
    else:
        return "No heartbeat"

def determine_heartbeat_status(last_hb_time, current_time, interval=600):
    """
    Determine if a heartbeat is online based on its last timestamp.
    
    Args:
        last_hb_time: The heartbeat timestamp
        current_time: The current time
        interval: Heartbeat interval in seconds (default: 600)
        
    Returns:
        String "Online" or "Offline"
    """
    timeout_seconds = interval * 2
    if last_hb_time and (current_time - last_hb_time) <= timedelta(seconds=timeout_seconds):
        return "Online"
    return "Offline"