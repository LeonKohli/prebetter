import pytest
from datetime import datetime, timedelta, UTC
from typing import Dict, List
from app.core.datetime_utils import ensure_timezone

def test_statistics_summary(auth_client):
    """Test getting statistics summary from the database"""
    response = auth_client.get("/api/v1/statistics/summary?time_range=24")
    
    # Verify response structure
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "total_alerts" in data
    assert "alerts_by_severity" in data
    assert "alerts_by_classification" in data
    assert "alerts_by_analyzer" in data
    assert "alerts_by_source_ip" in data
    assert "alerts_by_target_ip" in data
    assert "time_range_hours" in data
    assert "start_at" in data
    assert "end_at" in data
    
    # Verify data types
    assert isinstance(data["total_alerts"], int)
    assert isinstance(data["alerts_by_severity"], dict)
    assert isinstance(data["alerts_by_classification"], dict)
    assert isinstance(data["alerts_by_analyzer"], dict)
    assert isinstance(data["alerts_by_source_ip"], dict)
    assert isinstance(data["alerts_by_target_ip"], dict)
    assert isinstance(data["time_range_hours"], int)
    assert isinstance(data["start_at"], str)
    assert isinstance(data["end_at"], str)
    
    # Verify time range is correct
    assert data["time_range_hours"] == 24
    
    # Verify distributions contain expected data types
    for severity, count in data["alerts_by_severity"].items():
        assert isinstance(severity, str)
        assert isinstance(count, int)
    
    for classification, count in data["alerts_by_classification"].items():
        assert isinstance(classification, str)
        assert isinstance(count, int)
    
    for analyzer, count in data["alerts_by_analyzer"].items():
        assert isinstance(analyzer, str)
        assert isinstance(count, int)
    
    for ip, count in data["alerts_by_source_ip"].items():
        assert isinstance(ip, str)
        assert isinstance(count, int)
    
    for ip, count in data["alerts_by_target_ip"].items():
        assert isinstance(ip, str)
        assert isinstance(count, int)
    
    # Verify time range consistency (optional but good)
    try:
        start_dt = datetime.fromisoformat(data["start_at"])
        end_dt = datetime.fromisoformat(data["end_at"])
        # Calculate the actual time difference in hours
        actual_hours = (end_dt - start_dt).total_seconds() / 3600
        # Allow for a small tolerance due to how time ranges might be calculated
        assert abs(actual_hours - data["time_range_hours"]) < 0.1, \
            f"Reported time range {data['time_range_hours']} hours does not match calculated range {actual_hours:.2f} hours"
    except ValueError:
        pytest.fail("Could not parse start_at or end_at timestamps")
    
    # Print some debug info about what we found
    print(f"\nTotal alerts in last 24 hours: {data['total_alerts']}")
    if data["alerts_by_severity"]:
        print(f"Top severity: {max(data['alerts_by_severity'].items(), key=lambda x: x[1])[0]}")
    if data["alerts_by_classification"]:
        print(f"Top classification: {max(data['alerts_by_classification'].items(), key=lambda x: x[1])[0]}")

def test_timeline(auth_client):
    """Test getting timeline data with different time frames"""
    # Test hourly timeline
    response = auth_client.get("/api/v1/statistics/timeline?time_frame=hour")
    
    # Verify response structure
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "time_frame" in data
    assert "start_date" in data
    assert "end_date" in data
    assert "data" in data
    
    # Verify data types
    assert data["time_frame"] == "hour"
    assert isinstance(data["start_date"], str)
    assert isinstance(data["end_date"], str)
    assert isinstance(data["data"], list)
    
    # Verify timeline data points
    for point in data["data"]:
        assert "timestamp" in point
        assert "total" in point
        assert isinstance(point["timestamp"], str)
        assert isinstance(point["total"], int)
        assert point["total"] >= 0  # Total should never be negative
    
    # Verify chronological order
    if len(data["data"]) > 1:
        timestamps = [point["timestamp"] for point in data["data"]]
        assert timestamps == sorted(timestamps)
    
    # Test with filters
    filtered_response = auth_client.get(
        "/api/v1/statistics/timeline?time_frame=day&severity=high&classification=scan"
    )
    assert filtered_response.status_code == 200
    filtered_data = filtered_response.json()
    
    # Verify filtered data structure
    assert isinstance(filtered_data["data"], list)
    assert all(isinstance(point["total"], int) for point in filtered_data["data"])
    
    # Print some debug info
    print(f"\nTimeline data points: {len(data['data'])}")
    if data["data"]:
        total_alerts = sum(point["total"] for point in data["data"])
        print(f"Total alerts in timeline: {total_alerts}")
        print(f"Time range: {data['start_date']} to {data['end_date']}")

def test_timeline_time_frames(auth_client):
    """Test timeline endpoint with different time frames"""
    time_frames = ["hour", "day", "week", "month"]
    
    for time_frame in time_frames:
        response = auth_client.get(f"/api/v1/statistics/timeline?time_frame={time_frame}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify time frame is correct
        assert data["time_frame"] == time_frame
        
        # Verify data points are properly spaced
        if len(data["data"]) > 1:
            timestamps = [ensure_timezone(datetime.fromisoformat(point["timestamp"])) for point in data["data"]]
            time_diff = timestamps[1] - timestamps[0]
            
            # Verify time difference based on time frame
            if time_frame == "hour":
                assert time_diff.seconds == 3600  # 1 hour
            elif time_frame == "day":
                assert time_diff.days == 1
            elif time_frame == "week":
                assert time_diff.days == 7
            elif time_frame == "month":
                assert 28 <= time_diff.days <= 31
    
    # Test invalid time frame
    response = auth_client.get("/api/v1/statistics/timeline?time_frame=invalid")
    assert response.status_code in [400, 422]

def test_timeline_group_by(auth_client):
    """Test timeline endpoint with different group by options"""
    group_by_options = ["severity", "classification", "analyzer", "source", "target"]
    
    for group_by in group_by_options:
        response = auth_client.get(f"/api/v1/statistics/timeline?time_frame=hour&group_by={group_by}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify data structure includes grouping
        if data["data"]:
            point = data["data"][0]
            # Format has changed to use dictionary structures by type
            if group_by == "severity":
                assert "by_severity" in point
                assert len(point["by_severity"]) > 0
            elif group_by == "classification":
                assert "by_classification" in point
                assert len(point["by_classification"]) > 0
            elif group_by == "analyzer":
                assert "by_analyzer" in point
                assert len(point["by_analyzer"]) > 0
            elif group_by in ["source", "target"]:
                # These parameters still affect the query but data is still structured in dictionaries
                assert "by_severity" in point
    
    # Test invalid group by - should return 200 but without grouped data
    response = auth_client.get("/api/v1/statistics/timeline?time_frame=hour&group_by=invalid")
    assert response.status_code == 200
    data = response.json()
    
    # The response should still have the basic structure
    if data["data"]:
        point = data["data"][0]
        # Basic fields should be present
        assert "timestamp" in point
        assert "total" in point
        # Dictionary groupings should still be present
        assert "by_severity" in point
        assert "by_classification" in point
        assert "by_analyzer" in point

def test_statistics_summary_edge_cases(auth_client):
    """Test edge cases for statistics summary endpoint"""
    # Test minimum time range
    response = auth_client.get("/api/v1/statistics/summary?time_range=1")
    assert response.status_code == 200
    
    # Test maximum time range
    response = auth_client.get("/api/v1/statistics/summary?time_range=720")
    assert response.status_code == 200
    
    # Test invalid time ranges
    response = auth_client.get("/api/v1/statistics/summary?time_range=0")
    assert response.status_code in [400, 422]
    
    response = auth_client.get("/api/v1/statistics/summary?time_range=721")
    assert response.status_code in [400, 422]
    
    response = auth_client.get("/api/v1/statistics/summary?time_range=-1")
    assert response.status_code in [400, 422]
    
    # Test non-numeric time range
    response = auth_client.get("/api/v1/statistics/summary?time_range=abc")
    assert response.status_code in [400, 422]
    
    # Verify time range affects results
    short_range = auth_client.get("/api/v1/statistics/summary?time_range=1").json()
    long_range = auth_client.get("/api/v1/statistics/summary?time_range=24").json()
    
    # The longer time range should include at least as many alerts as the shorter one
    assert long_range["total_alerts"] >= short_range["total_alerts"]