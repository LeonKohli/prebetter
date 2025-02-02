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