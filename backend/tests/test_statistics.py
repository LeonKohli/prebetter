
def test_statistics_summary(client):
    """Test getting statistics summary from the database"""
    response = client.get("/api/v1/statistics/summary?time_range=24")
    
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
    assert "start_time" in data
    assert "end_time" in data
    
    # Verify data types
    assert isinstance(data["total_alerts"], int)
    assert isinstance(data["alerts_by_severity"], dict)
    assert isinstance(data["alerts_by_classification"], dict)
    assert isinstance(data["alerts_by_analyzer"], dict)
    assert isinstance(data["alerts_by_source_ip"], dict)
    assert isinstance(data["alerts_by_target_ip"], dict)
    assert isinstance(data["time_range_hours"], int)
    assert isinstance(data["start_time"], str)
    assert isinstance(data["end_time"], str)
    
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
    
    # Print some debug info about what we found
    print(f"\nTotal alerts in last 24 hours: {data['total_alerts']}")
    if data["alerts_by_severity"]:
        print(f"Top severity: {max(data['alerts_by_severity'].items(), key=lambda x: x[1])[0]}")
    if data["alerts_by_classification"]:
        print(f"Top classification: {max(data['alerts_by_classification'].items(), key=lambda x: x[1])[0]}")

def test_timeline(client):
    """Test getting timeline data with different time frames"""
    # Test hourly timeline
    response = client.get("/api/v1/statistics/timeline?time_frame=hour")
    
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
        assert "count" in point
        assert isinstance(point["timestamp"], str)
        assert isinstance(point["count"], int)
        assert point["count"] >= 0  # Count should never be negative
    
    # Verify chronological order
    if len(data["data"]) > 1:
        timestamps = [point["timestamp"] for point in data["data"]]
        assert timestamps == sorted(timestamps)
    
    # Test with filters
    filtered_response = client.get(
        "/api/v1/statistics/timeline?time_frame=day&severity=high&classification=scan"
    )
    assert filtered_response.status_code == 200
    filtered_data = filtered_response.json()
    
    # Verify filtered data structure
    assert isinstance(filtered_data["data"], list)
    assert all(isinstance(point["count"], int) for point in filtered_data["data"])
    
    # Print some debug info
    print(f"\nTimeline data points: {len(data['data'])}")
    if data["data"]:
        total_alerts = sum(point["count"] for point in data["data"])
        print(f"Total alerts in timeline: {total_alerts}")
        print(f"Time range: {data['start_date']} to {data['end_date']}") 