from datetime import datetime, timezone, timedelta

from app.database.models import (
    alert_result_to_list_item,
    build_analyzer_info,
    build_node_info,
    build_process_info,
    clean_byte_string,
    determine_heartbeat_status,
    format_relative_time,
    grouped_alert_to_response,
    process_additional_data,
    process_grouped_alerts_details,
)
from app.schemas.prelude import (
    AlertListItem,
    AnalyzerInfo,
    NodeInfo,
    GroupedAlert,
    GroupedAlertDetail,
    ProcessInfo,
    AnalyzerTimeInfo,
)


# Helper to simulate SQLAlchemy Row objects for testing
class MockRow:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getattr__(self, name):
        # Return None for missing attributes to mimic Row behavior
        return None


# --- Tests for alert_result_to_list_item ---


def test_alert_result_to_list_item_full():
    """Test conversion with all fields present."""
    mock_data = {
        "_ident": 12345,
        "messageid": "msg-001",
        "create_time": datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc),
        "create_time_usec": 500,
        "create_time_gmtoff": 0,
        "detect_time": datetime(2023, 10, 26, 10, 0, 5, tzinfo=timezone.utc),
        "detect_time_usec": 600,
        "detect_time_gmtoff": 0,
        "classification_text": "Test Classification",
        "severity": "high",
        "source_ipv4": "192.168.1.100",
        "target_ipv4": "10.0.0.5",
        "analyzer_name": "TestAnalyzer",
        "analyzer_host": "analyzer.example.com",
        "analyzer_model": "ModelX",
        "analyzer_manufacturer": "Manu Inc.",
        "analyzer_version": "1.1",
        "analyzer_class": "IDS",
        "analyzer_ostype": "Linux",
        "analyzer_osversion": "5.10",
        "node_location": "Server Room",
        "node_category": "Production",
    }
    mock_row = MockRow(**mock_data)

    result = alert_result_to_list_item(mock_row)  # type: ignore[arg-type]

    assert isinstance(result, AlertListItem)
    assert result.id == "12345"
    assert result.message_id == "msg-001"
    assert result.classification_text == "Test Classification"
    assert result.severity == "high"
    assert result.source_ipv4 == "192.168.1.100"
    assert result.target_ipv4 == "10.0.0.5"

    assert result.created_at is not None
    assert result.created_at.timestamp == mock_data["create_time"]
    assert result.created_at.usec == 500

    assert result.detected_at is not None
    assert result.detected_at.timestamp == mock_data["detect_time"]
    assert result.detected_at.usec == 600

    assert result.analyzer is not None
    assert result.analyzer.name == "TestAnalyzer (analyzer)"  # Checks hostname split
    assert result.analyzer.model == "ModelX"
    assert result.analyzer.manufacturer == "Manu Inc."
    assert result.analyzer.version == "1.1"
    assert result.analyzer.class_type == "IDS"
    assert result.analyzer.ostype == "Linux"
    assert result.analyzer.osversion == "5.10"

    assert result.analyzer.node is not None
    assert result.analyzer.node.name == "analyzer.example.com"
    assert result.analyzer.node.location == "Server Room"
    assert result.analyzer.node.category == "Production"


def test_alert_result_to_list_item_minimal():
    """Test conversion with only required fields and minimal related data."""
    mock_data = {
        "_ident": 54321,
        "messageid": "msg-002",
        "detect_time": datetime(2023, 10, 27, 11, 0, 0, tzinfo=timezone.utc),
        "classification_text": "Minimal Alert",
        "severity": "low",
        # Missing create_time, source/target IPs, most analyzer/node fields
        "analyzer_name": "BasicAnalyzer",
    }
    mock_row = MockRow(**mock_data)

    result = alert_result_to_list_item(mock_row)  # type: ignore[arg-type]

    assert isinstance(result, AlertListItem)
    assert result.id == "54321"
    assert result.message_id == "msg-002"
    assert result.classification_text == "Minimal Alert"
    assert result.severity == "low"
    assert result.source_ipv4 is None
    assert result.target_ipv4 is None
    assert result.created_at is None

    assert result.detected_at is not None
    assert result.detected_at.timestamp == mock_data["detect_time"]
    assert result.detected_at.usec is None

    assert result.analyzer is not None
    assert result.analyzer.name == "BasicAnalyzer"  # No host to split
    assert result.analyzer.model is None
    assert (
        result.analyzer.node is None
    )  # Node info depends on host, location, or category


def test_alert_result_to_list_item_no_analyzer_or_node():
    """Test conversion when analyzer and node info are completely missing."""
    mock_data = {
        "_ident": 999,
        "messageid": "msg-003",
        "detect_time": datetime(2023, 10, 28, 12, 0, 0, tzinfo=timezone.utc),
        "classification_text": "No Analyzer",
        "severity": "medium",
    }
    mock_row = MockRow(**mock_data)

    result = alert_result_to_list_item(mock_row)  # type: ignore[arg-type]

    assert isinstance(result, AlertListItem)
    assert result.id == "999"
    assert result.detected_at is not None
    assert result.analyzer is None  # Should be None if analyzer_name is missing


# --- Tests for grouped_alert_to_response ---


def test_grouped_alert_to_response():
    pair_data = {
        "source_ipv4": "1.1.1.1",
        "target_ipv4": "2.2.2.2",
        "total_count": 15,
    }
    pair_row = MockRow(**pair_data)

    alert_detail_1 = GroupedAlertDetail(
        classification="Class A",
        count=10,
        analyzer=["Analyzer1"],
        analyzer_host=["host1"],
        detected_at=datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc),
    )
    alert_detail_2 = GroupedAlertDetail(
        classification="Class B",
        count=5,
        analyzer=["Analyzer2"],
        analyzer_host=["host2"],
        detected_at=datetime(2023, 10, 26, 11, 0, 0, tzinfo=timezone.utc),
    )
    alerts_map = {("1.1.1.1", "2.2.2.2"): [alert_detail_1, alert_detail_2]}

    result = grouped_alert_to_response(pair_row, alerts_map)  # type: ignore[arg-type]

    assert isinstance(result, GroupedAlert)
    assert result.source_ipv4 == "1.1.1.1"
    assert result.target_ipv4 == "2.2.2.2"
    assert result.total_count == 15
    assert len(result.alerts) == 2
    assert result.alerts[0].classification == "Class A"
    assert result.alerts[1].classification == "Class B"


def test_grouped_alert_to_response_no_matching_alerts():
    pair_data = {"source_ipv4": "3.3.3.3", "target_ipv4": "4.4.4.4", "total_count": 5}
    pair_row = MockRow(**pair_data)
    alerts_map = {}  # Empty map

    result = grouped_alert_to_response(pair_row, alerts_map)  # type: ignore[arg-type]

    assert result.source_ipv4 == "3.3.3.3"
    assert result.total_count == 5
    assert len(result.alerts) == 0  # Should have an empty list of alerts


# --- Tests for process_grouped_alerts_details ---


def test_process_grouped_alerts_details_basic():
    alert_data_1 = {
        "source_ipv4": "1.1.1.1",
        "target_ipv4": "2.2.2.2",
        "classification": "Class A",
        "count": 10,
        "analyzers": "Analyzer1,AnalyzerX",
        "analyzer_hosts": "host1.domain.tld,hostX.domain.tld",
        "latest_time": datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc),
    }
    alert_data_2 = {
        "source_ipv4": "1.1.1.1",
        "target_ipv4": "2.2.2.2",
        "classification": "Class B",
        "count": 5,
        "analyzers": "Analyzer2",
        "analyzer_hosts": "host2.domain.tld",
        "latest_time": datetime(2023, 10, 26, 11, 0, 0, tzinfo=timezone.utc),
    }
    alert_data_3 = {
        "source_ipv4": "3.3.3.3",
        "target_ipv4": "4.4.4.4",
        "classification": "Class C",
        "count": 2,
        "analyzers": "Analyzer3",
        "analyzer_hosts": "host3.domain.tld",
        "latest_time": datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
    }
    alerts = [MockRow(**alert_data_1), MockRow(**alert_data_2), MockRow(**alert_data_3)]

    result_map = process_grouped_alerts_details(alerts)

    assert len(result_map) == 2  # Two distinct pairs
    assert ("1.1.1.1", "2.2.2.2") in result_map
    assert ("3.3.3.3", "4.4.4.4") in result_map

    pair1_alerts = result_map[("1.1.1.1", "2.2.2.2")]
    assert len(pair1_alerts) == 2
    assert pair1_alerts[0].classification == "Class A"
    assert pair1_alerts[0].count == 10
    assert pair1_alerts[0].analyzer == ["Analyzer1", "AnalyzerX"]
    assert pair1_alerts[0].analyzer_host == ["host1", "hostX"]  # Check hostname split
    assert pair1_alerts[0].detected_at == alert_data_1["latest_time"]

    assert pair1_alerts[1].classification == "Class B"
    assert pair1_alerts[1].analyzer == ["Analyzer2"]
    assert pair1_alerts[1].analyzer_host == ["host2"]

    pair2_alerts = result_map[("3.3.3.3", "4.4.4.4")]
    assert len(pair2_alerts) == 1
    assert pair2_alerts[0].classification == "Class C"
    assert pair2_alerts[0].analyzer_host == ["host3"]


def test_process_grouped_alerts_details_empty_and_none():
    """Test handling of empty inputs, None classifications, and empty strings."""
    alert_data_1 = {
        "source_ipv4": "1.1.1.1",
        "target_ipv4": "2.2.2.2",
        "classification": None,  # Should be skipped
        "count": 5,
        "analyzers": None,
        "analyzer_hosts": None,
        "latest_time": datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc),
    }
    alert_data_2 = {
        "source_ipv4": "1.1.1.1",
        "target_ipv4": "2.2.2.2",
        "classification": "Class A",
        "count": 10,
        "analyzers": "",  # Empty string
        "analyzer_hosts": ",,",  # Empty strings from split
        "latest_time": datetime(2023, 10, 26, 11, 0, 0, tzinfo=timezone.utc),
    }
    alerts = [MockRow(**alert_data_1), MockRow(**alert_data_2)]

    result_map = process_grouped_alerts_details(alerts)

    assert len(result_map) == 1
    assert ("1.1.1.1", "2.2.2.2") in result_map
    pair_alerts = result_map[("1.1.1.1", "2.2.2.2")]
    assert len(pair_alerts) == 1  # Only alert_data_2 should be included
    assert pair_alerts[0].classification == "Class A"
    assert pair_alerts[0].analyzer == []  # Should be empty list
    assert pair_alerts[0].analyzer_host == []  # Should be empty list


def test_process_grouped_alerts_details_max_limit():
    """Test that processing stops after reaching the internal max limit."""
    # Create more alerts than the internal limit (currently 1000)
    alerts = []
    for i in range(1005):
        alerts.append(
            MockRow(
                **{
                    "source_ipv4": f"1.1.1.{i % 256}",
                    "target_ipv4": f"2.2.2.{i % 256}",
                    "classification": f"Class {i}",
                    "count": 1,
                    "analyzers": "Analyzer",
                    "analyzer_hosts": "host.domain",
                    "latest_time": datetime.now(timezone.utc),
                }
            )
        )

    result_map = process_grouped_alerts_details(alerts)

    # Check that the number of processed alerts respects the limit
    total_processed = sum(len(details) for details in result_map.values())
    assert total_processed == 1000


# --- Tests for build_analyzer_info ---


def test_build_analyzer_info_full():
    analyzer_data = MockRow(
        **{
            "name": "Test Analyzer",
            "analyzerid": "aid-123",
            "model": "Model Y",
            "manufacturer": "Maker Co.",
            "version": "2.0",
            "class": "Firewall",
            "ostype": "FreeBSD",
            "osversion": "13.0",
            "_index": -1,  # Primary
        }
    )
    node_info = NodeInfo(name="node1", location="DMZ", category="Edge")
    process_info = ProcessInfo(name="fw_proc", pid=1234, path="/usr/bin/fw")
    analyzer_time_info = AnalyzerTimeInfo(
        timestamp=datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc),
        usec=100,
        gmtoff=0,
    )

    result = build_analyzer_info(
        analyzer_data,
        node_info=node_info,
        process_info=process_info,
        analyzer_time_info=analyzer_time_info,
    )

    assert isinstance(result, AnalyzerInfo)
    assert result.name == "Test Analyzer"
    assert result.analyzer_id == "aid-123"
    assert result.model == "Model Y"
    assert result.manufacturer == "Maker Co."
    assert result.version == "2.0"
    assert result.class_type == "Firewall"
    assert result.ostype == "FreeBSD"
    assert result.osversion == "13.0"
    assert result.node == node_info
    assert result.process == process_info
    assert result.analyzer_time == analyzer_time_info
    assert result.chain_index == -1
    assert result.role == "Primary"


def test_build_analyzer_info_minimal():
    analyzer_data = MockRow(name="Minimal Analyzer")  # Only name

    result = build_analyzer_info(analyzer_data)

    assert isinstance(result, AnalyzerInfo)
    assert result.name == "Minimal Analyzer"
    assert result.analyzer_id is None
    assert result.model is None
    assert result.node is None
    assert result.process is None
    assert result.analyzer_time is None
    assert result.chain_index is None
    assert result.role is None  # Role depends on index


def test_build_analyzer_info_roles():
    primary = MockRow(name="Primary", _index=-1)
    secondary = MockRow(name="Secondary", _index=0)
    concentrator = MockRow(name="Concentrator", _index=1, **{"class": "Concentrator"})
    other_secondary = MockRow(name="OtherSecondary", _index=2, **{"class": "Other"})

    assert build_analyzer_info(primary).role == "Primary"
    assert build_analyzer_info(secondary).role == "Secondary"
    assert build_analyzer_info(concentrator).role == "Concentrator"
    assert build_analyzer_info(other_secondary).role == "Secondary"


# --- Tests for build_node_info ---


def test_build_node_info_full():
    node_data = MockRow(
        **{
            "name": "Node Alpha",
            "location": "Rack 1",
            "category": "Testing",
            "ident": "node-alpha-id",
        }
    )
    result = build_node_info(node_data)
    assert isinstance(result, NodeInfo)
    assert result.name == "Node Alpha"
    assert result.location == "Rack 1"
    assert result.category == "Testing"
    assert result.ident == "node-alpha-id"


def test_build_node_info_minimal():
    node_data = MockRow(name="Node Beta")  # Only name
    result = build_node_info(node_data)
    assert isinstance(result, NodeInfo)
    assert result.name == "Node Beta"
    assert result.location is None
    assert result.category is None
    assert result.ident is None


def test_build_node_info_none():
    assert build_node_info(None) is None


# --- Tests for build_process_info ---


def test_build_process_info_full():
    process_data = MockRow(name="app.exe", pid=5678, path="C:\\Apps")
    process_args = [("-config",), ("file.conf",)]
    process_env = [("PATH=/usr/bin",), ("TEMP=/tmp",)]

    result = build_process_info(process_data, process_args, process_env)
    assert isinstance(result, ProcessInfo)
    assert result.name == "app.exe"
    assert result.pid == 5678
    assert result.path == "C:\\Apps"
    assert result.args == ["-config", "file.conf"]
    assert result.env == ["PATH=/usr/bin", "TEMP=/tmp"]


def test_build_process_info_minimal():
    process_data = MockRow(name="proc")
    result = build_process_info(process_data)
    assert isinstance(result, ProcessInfo)
    assert result.name == "proc"
    assert result.pid is None
    assert result.path is None
    assert result.args == []
    assert result.env == []


def test_build_process_info_none():
    assert build_process_info(None) is None


# --- Tests for clean_byte_string ---


def test_clean_byte_string_valid():
    assert clean_byte_string("b'hello world'") == "hello world"
    assert clean_byte_string('b"another test"') == "another test"


def test_clean_byte_string_not_bytes():
    assert clean_byte_string("just a regular string") == "just a regular string"
    assert clean_byte_string("number 123") == "number 123"


def test_clean_byte_string_malformed():
    assert (
        clean_byte_string("b'unclosed string") == "b'unclosed string"
    )  # Return original if malformed
    assert clean_byte_string("'missing b'") == "'missing b'"


def test_clean_byte_string_empty_none():
    assert clean_byte_string("") == ""
    # clean_byte_string expects a string, not None
    # This test should be removed or the function should handle None


# --- Tests for process_additional_data ---


def test_process_additional_data_basic():
    add_data_rows = [
        MockRow(meaning="Payload", type="string", data="b'Sample Payload'"),
        MockRow(meaning="Count", type="integer", data="10"),
        MockRow(meaning="Enabled", type="boolean", data="true"),
        MockRow(meaning="FloatVal", type="float", data="3.14"),
        MockRow(meaning="InvalidInt", type="integer", data="abc"),  # Invalid conversion
        MockRow(
            meaning="InvalidBool", type="boolean", data="maybe"
        ),  # Invalid conversion
        MockRow(meaning="InvalidFloat", type="float", data="def"),  # Invalid conversion
        MockRow(meaning="OtherType", type="other", data="keep as string"),
        MockRow(meaning="EmptyValue", type="string", data=""),
    ]

    result = process_additional_data(add_data_rows)

    expected = {
        "Payload": "Sample Payload",  # Cleaned byte string
        "Count": 10,
        "Enabled": True,
        "FloatVal": 3.14,
        "InvalidInt": "abc",  # Keep original on error
        "InvalidBool": "maybe",  # Keep original on error
        "InvalidFloat": "def",  # Keep original on error
        "OtherType": "keep as string",
        "EmptyValue": "",
    }
    assert result == expected


def test_process_additional_data_byte_string_formats():
    payload_bytes = b"\x00ABCDEF\xff\x10"  # include non-utf8 bytes
    add_data_rows = [
        MockRow(meaning="Payload", type="byte-string", data=payload_bytes),
    ]

    result = process_additional_data(add_data_rows)

    assert "Payload" in result
    payload = result["Payload"]
    assert isinstance(payload, dict)
    # readable exists and is a string (with replacement for undecodable bytes)
    assert isinstance(payload.get("readable"), str)
    # original is base64 of original bytes
    import base64
    assert payload.get("original") == base64.b64encode(payload_bytes).decode("ascii")


def test_process_additional_data_empty():
    assert process_additional_data([]) == {}
    assert process_additional_data(None) == {}


# --- Tests for format_relative_time ---


def test_format_relative_time():
    now = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    assert format_relative_time(now - timedelta(seconds=5), now) == "5 seconds ago"
    assert format_relative_time(now - timedelta(seconds=59), now) == "59 seconds ago"
    assert format_relative_time(now - timedelta(minutes=1), now) == "1 minute ago"
    assert (
        format_relative_time(now - timedelta(minutes=1, seconds=30), now)
        == "1 minute ago"
    )
    assert format_relative_time(now - timedelta(minutes=59), now) == "59 minutes ago"
    assert format_relative_time(now - timedelta(hours=1), now) == "1 hour ago"
    assert (
        format_relative_time(now - timedelta(hours=1, minutes=30), now) == "1 hour ago"
    )
    assert format_relative_time(now - timedelta(hours=23), now) == "23 hours ago"
    assert format_relative_time(now - timedelta(days=1), now) == "1 day ago"
    assert format_relative_time(now - timedelta(days=1, hours=12), now) == "1 day ago"
    assert format_relative_time(now - timedelta(days=6), now) == "6 days ago"
    assert format_relative_time(now - timedelta(days=7), now) == "1 week ago"
    assert format_relative_time(now - timedelta(days=13), now) == "1 week ago"
    assert format_relative_time(now - timedelta(days=14), now) == "2 weeks ago"
    assert format_relative_time(now - timedelta(days=29), now) == "4 weeks ago"
    assert format_relative_time(now - timedelta(days=30), now) == "1 month ago"
    assert format_relative_time(now - timedelta(days=50), now) == "1 month ago"
    assert format_relative_time(now - timedelta(days=60), now) == "2 months ago"
    assert format_relative_time(now - timedelta(days=364), now) == "12 months ago"
    assert format_relative_time(now - timedelta(days=365), now) == "1 year ago"
    assert format_relative_time(now - timedelta(days=700), now) == "1 year ago"
    assert format_relative_time(now - timedelta(days=730), now) == "2 years ago"


def test_format_relative_time_future_none():
    now = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    assert format_relative_time(now + timedelta(seconds=5), now) == "in the future"
    assert format_relative_time(None, now) == "never"


# --- Tests for determine_heartbeat_status ---


def test_determine_heartbeat_status():
    now = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    interval_seconds = 600  # 10 minutes

    # Active (within interval)
    active_time = now - timedelta(seconds=interval_seconds - 1)
    assert determine_heartbeat_status(active_time, now, interval_seconds) == "active"

    # Inactive (just outside interval)
    inactive_time = now - timedelta(seconds=interval_seconds + 1)
    assert (
        determine_heartbeat_status(inactive_time, now, interval_seconds) == "inactive"
    )

    # Offline (more than 2x interval)
    offline_time = now - timedelta(seconds=(interval_seconds * 2) + 1)
    assert determine_heartbeat_status(offline_time, now, interval_seconds) == "offline"

    # Edge case: exactly on interval boundary (should be active)
    exact_interval_time = now - timedelta(seconds=interval_seconds)
    assert (
        determine_heartbeat_status(exact_interval_time, now, interval_seconds)
        == "active"
    )

    # Edge case: exactly on 2x interval boundary (should be inactive)
    exact_2x_interval_time = now - timedelta(seconds=interval_seconds * 2)
    assert (
        determine_heartbeat_status(exact_2x_interval_time, now, interval_seconds)
        == "inactive"
    )

    # Future time (should be treated as active/current)
    future_time = now + timedelta(minutes=5)
    assert determine_heartbeat_status(future_time, now, interval_seconds) == "active"


def test_determine_heartbeat_status_none():
    now = datetime.now(timezone.utc)
    assert (
        determine_heartbeat_status(None, now) == "unknown"
    )  # Status is unknown if no last heartbeat
