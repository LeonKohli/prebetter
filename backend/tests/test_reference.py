from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    """Test the root endpoint that provides API status and documentation links"""
    response = client.get("/")
    
    # Verify response structure
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "status" in data
    assert "message" in data
    assert "version" in data
    assert "docs_url" in data
    assert "redoc_url" in data
    
    # Verify the expected values
    assert data["status"] == "online"
    assert data["message"] == "Welcome to Prelude SIEM API"
    assert data["version"] == "1.0.0"
    assert data["docs_url"] == "/docs"
    assert data["redoc_url"] == "/redoc"

def test_get_unique_classifications():
    """Test getting classifications from the real database"""
    response = client.get("/api/v1/classifications")
    
    # Verify response structure
    assert response.status_code == 200
    classifications = response.json()
    
    # Verify we got a list of strings
    assert isinstance(classifications, list)
    assert all(isinstance(item, str) for item in classifications)
    
    # Verify the list is not empty (assuming the real database has classifications)
    assert len(classifications) > 0
    
    # Verify no duplicates
    assert len(classifications) == len(set(classifications))
    
    # Verify the list is sorted (case-insensitive)
    sorted_classifications = sorted(classifications, key=str.lower)
    assert classifications == sorted_classifications
    
    # Print some debug info about what we found
    print(f"\nFound {len(classifications)} unique classifications")
    if len(classifications) > 0:
        print(f"Sample classifications: {classifications[:3]}")

def test_statistics_summary():
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