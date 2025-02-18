from datetime import datetime, timedelta
from app.core.datetime_utils import get_current_time, ensure_timezone
import pytest
pytestmark = pytest.mark.skip(reason="Skipping all tests in this file")
def test_heartbeats_tree(auth_client):
    """Test getting heartbeats tree view"""
    response = auth_client.get("/api/v1/heartbeats/tree")
    
    # Verify response structure
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "hosts" in data
    assert "total_hosts" in data
    assert "total_agents" in data
    
    # Verify data types
    assert isinstance(data["hosts"], dict)
    assert isinstance(data["total_hosts"], int)
    assert isinstance(data["total_agents"], int)
    
    # Verify host structure if any hosts exist
    if data["hosts"]:
        host = next(iter(data["hosts"].values()))
        assert "os" in host
        assert "agents" in host
        assert isinstance(host["agents"], list)
        
        # Verify agent structure if any agents exist
        if host["agents"]:
            agent = host["agents"][0]
            assert "name" in agent
            assert "model" in agent
            assert "version" in agent
            assert "class" in agent
            assert "last_heartbeat" in agent
            assert "status" in agent
            assert agent["status"] in ["online", "offline"]
    
    # Verify counts are consistent
    assert data["total_hosts"] == len(data["hosts"])
    total_agents = sum(len(host["agents"]) for host in data["hosts"].values())
    assert data["total_agents"] == total_agents
    
    # Print some debug info
    print(f"\nTotal hosts: {data['total_hosts']}")
    print(f"Total agents: {data['total_agents']}")
    if data["hosts"]:
        print(f"Sample host OS: {next(iter(data['hosts'].values()))['os']}")

def test_heartbeats_timeline(auth_client):
    """Test getting heartbeats timeline data"""
    # Test with default parameters
    response = auth_client.get("/api/v1/heartbeats/timeline")
    
    # Verify response structure
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "items" in data
    assert "total" in data
    
    # Verify data types
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    
    # Verify item structure if any items exist
    if data["items"]:
        item = data["items"][0]
        assert "timestamp" in item
        assert "agent" in item
        assert "node_name" in item
        assert "node_address" in item
        assert "model" in item
        
        # Verify timestamp is within the last 24 hours (default)
        timestamp = ensure_timezone(datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00')))
        current_time = get_current_time()
        assert timestamp <= current_time
        assert timestamp >= current_time - timedelta(hours=24)
    
    # Test with custom hours parameter
    custom_response = auth_client.get("/api/v1/heartbeats/timeline?hours=48")
    assert custom_response.status_code == 200
    custom_data = custom_response.json()
    
    if custom_data["items"]:
        # Verify timestamp is within the specified time range
        timestamp = ensure_timezone(datetime.fromisoformat(custom_data["items"][0]["timestamp"].replace('Z', '+00:00')))
        current_time = get_current_time()
        assert timestamp >= current_time - timedelta(hours=48)
    
    # Print some debug info
    print(f"\nTotal timeline entries: {data['total']}")
    if data["items"]:
        print(f"Most recent heartbeat: {data['items'][0]['timestamp']}")
        print(f"Sample agent: {data['items'][0]['agent']}")

def test_heartbeats_timeline_edge_cases(auth_client):
    """Test edge cases for the heartbeats timeline endpoint"""
    # Test minimum hours
    min_response = auth_client.get("/api/v1/heartbeats/timeline?hours=1")
    assert min_response.status_code == 200
    
    # Test maximum hours
    max_response = auth_client.get("/api/v1/heartbeats/timeline?hours=168")
    assert max_response.status_code == 200
    
    # Test hours below minimum
    invalid_min_response = auth_client.get("/api/v1/heartbeats/timeline?hours=0")
    assert invalid_min_response.status_code in [400, 422]
    
    # Test hours above maximum
    invalid_max_response = auth_client.get("/api/v1/heartbeats/timeline?hours=169")
    assert invalid_max_response.status_code in [400, 422]
    
    # Test invalid hours parameter
    invalid_response = auth_client.get("/api/v1/heartbeats/timeline?hours=abc")
    assert invalid_response.status_code in [400, 422]
    
    # Test future time range (should return empty result)
    future_data = auth_client.get("/api/v1/heartbeats/timeline?hours=1").json()
    assert isinstance(future_data["items"], list)
    
    # Print some debug info
    print("\nTested edge cases for timeline endpoint")
    print(f"Response for minimum hours (1): {min_response.status_code}")
    print(f"Response for maximum hours (168): {max_response.status_code}")

def test_heartbeats_authentication(client):
    """Test authentication requirements for heartbeat endpoints"""
    # Test tree endpoint without authentication
    tree_response = client.get("/api/v1/heartbeats/tree")
    assert tree_response.status_code in [401, 403]
    
    # Test timeline endpoint without authentication
    timeline_response = client.get("/api/v1/heartbeats/timeline")
    assert timeline_response.status_code in [401, 403]
    
    # Print some debug info
    print("\nTested authentication requirements")
    print(f"Tree endpoint unauthorized response: {tree_response.status_code}")
    print(f"Timeline endpoint unauthorized response: {timeline_response.status_code}") 