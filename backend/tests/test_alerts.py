import pytest
from datetime import timedelta
from app.core.datetime_utils import get_current_time

future_start_date = get_current_time() + timedelta(days=365)
future_end_date = get_current_time() + timedelta(days=365 + 365)
    
def test_list_alerts(auth_client):
    """Test getting alerts list with various filters and sorting options"""
    # Test basic pagination
    response = auth_client.get("/api/v1/alerts/?page=1&size=10")
    
    # Verify response structure
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "total" in data
    assert "items" in data
    assert "page" in data
    assert "size" in data
    
    # Verify data types and pagination
    assert isinstance(data["total"], int)
    assert isinstance(data["items"], list)
    assert data["page"] == 1
    assert data["size"] == 10
    assert len(data["items"]) <= 10  # Should not exceed page size
    
    # Verify alert item structure
    if data["items"]:
        alert = data["items"][0]
        assert "alert_id" in alert
        assert "message_id" in alert
        assert "detect_time" in alert
        assert "severity" in alert
        assert isinstance(alert["alert_id"], str)
        
        # Verify time info structure if present
        if alert["detect_time"]:
            assert "time" in alert["detect_time"]
            assert "usec" in alert["detect_time"]
            assert "gmtoff" in alert["detect_time"]
    
    # Test sorting
    sort_response = auth_client.get("/api/v1/alerts/?sort_by=severity&sort_order=desc")
    assert sort_response.status_code == 200
    sort_data = sort_response.json()
    
    # Verify sorting works (if we have multiple items with severity)
    if len(sort_data["items"]) > 1:
        severities = [item["severity"] for item in sort_data["items"] if item["severity"]]
        if severities:
            assert severities == sorted(severities, reverse=True)
    
    # Test filtering
    filter_params = {
        "severity": "high",
        "classification": "scan",
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-12-31T23:59:59"
    }
    filter_response = auth_client.get("/api/v1/alerts/", params=filter_params)
    assert filter_response.status_code == 200
    filter_data = filter_response.json()
    
    # Verify filtered results
    if filter_data["items"]:
        # All items should match the severity filter if specified
        assert all(item["severity"] == "high" for item in filter_data["items"] if item["severity"])
        # All items should contain the classification text if specified
        assert all("scan" in item["classification_text"].lower() 
                  for item in filter_data["items"] 
                  if item["classification_text"])
    
    # Test invalid page/size parameters
    invalid_response = auth_client.get("/api/v1/alerts/?page=0&size=1000")
    assert invalid_response.status_code in [400, 422]  # FastAPI validation error
    
    # Print some debug info
    print(f"\nTotal alerts in database: {data['total']}")
    print(f"Alerts in first page: {len(data['items'])}")
    if data['items']:
        print(f"Sample alert classifications: {[item['classification_text'] for item in data['items'][:3] if item['classification_text']]}")

def test_alert_detail(auth_client):
    """Test getting detailed information for a specific alert"""
    # First get a list of alerts to find a valid ID
    list_response = auth_client.get("/api/v1/alerts/?page=1&size=1")
    assert list_response.status_code == 200
    alerts = list_response.json()
    
    if not alerts["items"]:
        pytest.skip("No alerts in database to test detail view")
    
    alert_id = alerts["items"][0]["alert_id"]
    
    # Test getting alert detail
    response = auth_client.get(f"/api/v1/alerts/{alert_id}")
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "alert_id" in data
    assert "message_id" in data
    assert "detect_time" in data
    
    # Verify optional fields have correct types when present
    if "create_time" in data and data["create_time"]:
        assert "time" in data["create_time"]
        assert "usec" in data["create_time"]
        assert "gmtoff" in data["create_time"]
    
    if "classification_text" in data:
        assert isinstance(data["classification_text"], str)
    
    if "severity" in data:
        assert isinstance(data["severity"], str)
    
    # Verify network information structure
    if "source" in data and data["source"]:
        assert "address" in data["source"]
        assert isinstance(data["source"]["address"], str)
    
    if "target" in data and data["target"]:
        assert "address" in data["target"]
        assert isinstance(data["target"]["address"], str)
    
    # Verify analyzer information
    if "analyzer" in data and data["analyzer"]:
        assert "name" in data["analyzer"]
        assert isinstance(data["analyzer"]["name"], str)
    
    # Test with payload truncation
    truncated_response = auth_client.get(f"/api/v1/alerts/{alert_id}?truncate_payload=true")
    assert truncated_response.status_code == 200
    
    # Test invalid alert ID
    invalid_response = auth_client.get("/api/v1/alerts/999999999")
    assert invalid_response.status_code == 404
    
    # Print some debug info
    print(f"\nTested alert detail for ID: {alert_id}")
    if "classification_text" in data:
        print(f"Classification: {data['classification_text']}")
    if "severity" in data:
        print(f"Severity: {data['severity']}")

def test_grouped_alerts(auth_client):
    """Test getting grouped alerts with various filters and sorting options"""
    # Test basic pagination
    response = auth_client.get("/api/v1/alerts/groups?page=1&size=10")
    
    # Verify response structure
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "total" in data
    assert "groups" in data
    assert "page" in data
    assert "size" in data
    
    # Verify data types and pagination
    assert isinstance(data["total"], int)
    assert isinstance(data["groups"], list)
    assert data["page"] == 1
    assert data["size"] == 10
    assert len(data["groups"]) <= 10  # Should not exceed page size
    
    # Verify group structure
    if data["groups"]:
        group = data["groups"][0]
        assert "source_ipv4" in group
        assert "target_ipv4" in group
        assert "total_count" in group
        assert "alerts" in group
        assert isinstance(group["alerts"], list)
        
        # Verify alert details in group
        if group["alerts"]:
            alert = group["alerts"][0]
            assert "classification" in alert
            assert "count" in alert
            assert "analyzer" in alert
            assert "analyzer_host" in alert
            assert "time" in alert
    
    # Test sorting
    sort_response = auth_client.get("/api/v1/alerts/groups?sort_by=severity&sort_order=desc")
    assert sort_response.status_code == 200
    
    # Test filtering
    filter_params = {
        "severity": "high",
        "classification": "scan",
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-12-31T23:59:59"
    }
    filter_response = auth_client.get("/api/v1/alerts/groups", params=filter_params)
    assert filter_response.status_code == 200
    
    # Test invalid parameters
    invalid_response = auth_client.get("/api/v1/alerts/groups?page=0&size=1000")
    assert invalid_response.status_code in [400, 422]  # FastAPI validation error

def test_list_alerts_edge_cases(auth_client):
    """Test edge cases for the list alerts endpoint"""
    # Test empty filters
    response = auth_client.get("/api/v1/alerts/?severity=&classification=")
    assert response.status_code == 200
    
    # Test invalid date format
    response = auth_client.get("/api/v1/alerts/?start_date=invalid-date")
    assert response.status_code in [400, 422]
    
    # Test invalid sort field
    response = auth_client.get("/api/v1/alerts/?sort_by=invalid_field")
    assert response.status_code in [400, 422]
    
    # Test invalid sort order
    response = auth_client.get("/api/v1/alerts/?sort_order=invalid")
    assert response.status_code in [400, 422]
    
    # Test future date range

    future_params = {
        "start_date": future_start_date.isoformat(),
        "end_date": future_end_date.isoformat()
    }
    response = auth_client.get("/api/v1/alerts/", params=future_params)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0  # Should return empty result for future dates

def test_alert_detail_edge_cases(auth_client):
    """Test edge cases for the alert detail endpoint"""
    # Test non-numeric alert ID
    response = auth_client.get("/api/v1/alerts/abc")
    assert response.status_code in [400, 422]
    
    # Test zero alert ID
    response = auth_client.get("/api/v1/alerts/0")
    assert response.status_code == 404
    
    # Test negative alert ID - should return 404 as negative IDs can't exist
    response = auth_client.get("/api/v1/alerts/-1")
    assert response.status_code == 404
    
    # Test very large alert ID
    response = auth_client.get("/api/v1/alerts/999999999999999")
    assert response.status_code == 404
    
    # Test truncate_payload parameter variations
    list_response = auth_client.get("/api/v1/alerts/?page=1&size=1")
    if list_response.json()["items"]:
        alert_id = list_response.json()["items"][0]["alert_id"]
        
        # Test explicit true/false values
        response = auth_client.get(f"/api/v1/alerts/{alert_id}?truncate_payload=true")
        assert response.status_code == 200
        
        response = auth_client.get(f"/api/v1/alerts/{alert_id}?truncate_payload=false")
        assert response.status_code == 200
        
        # Test invalid truncate_payload value
        response = auth_client.get(f"/api/v1/alerts/{alert_id}?truncate_payload=invalid")
        assert response.status_code in [400, 422]

def test_delete_alert(auth_client):
    """Test deleting an alert"""
    # First get an existing alert
    response = auth_client.get("/api/v1/alerts/?page=1&size=1")
    assert response.status_code == 200
    data = response.json()
    assert data["items"]
    
    alert_id = data["items"][0]["alert_id"]
    
    # Delete the alert
    delete_response = auth_client.delete(f"/api/v1/alerts/{alert_id}")
    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert "message" in delete_data
    assert delete_data["message"] == f"Alert {alert_id} and all related data successfully deleted"
    
    # Verify the alert is deleted by trying to fetch it
    get_response = auth_client.get(f"/api/v1/alerts/{alert_id}")
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Alert not found"
    
    # Verify it's also removed from the list
    list_response = auth_client.get("/api/v1/alerts/?page=1&size=10")
    assert list_response.status_code == 200
    list_data = list_response.json()
    alert_ids = [alert["alert_id"] for alert in list_data["items"]]
    assert alert_id not in alert_ids

def test_delete_alert_edge_cases(auth_client):
    """Test edge cases for alert deletion"""
    # Test deleting non-existent alert
    response = auth_client.delete("/api/v1/alerts/999999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"
    
    # Test deleting with invalid alert ID format
    response = auth_client.delete("/api/v1/alerts/invalid")
    assert response.status_code == 422  # FastAPI validation error
    
    # Test deleting already deleted alert
    # First get and delete an alert
    list_response = auth_client.get("/api/v1/alerts/?page=1&size=1")
    if list_response.json()["items"]:
        alert_id = list_response.json()["items"][0]["alert_id"]
        auth_client.delete(f"/api/v1/alerts/{alert_id}")
        
        # Try to delete it again
        second_delete = auth_client.delete(f"/api/v1/alerts/{alert_id}")
        assert second_delete.status_code == 404
        assert second_delete.json()["detail"] == "Alert not found" 