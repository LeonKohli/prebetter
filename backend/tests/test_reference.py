
def test_get_unique_classifications(client):
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

def test_get_unique_severities(client):
    """Test getting unique severity levels"""
    response = client.get("/api/v1/severities")
    
    # Verify response structure
    assert response.status_code == 200
    severities = response.json()
    
    # Verify we got a list of strings
    assert isinstance(severities, list)
    assert all(isinstance(item, str) for item in severities)
    
    # Verify no duplicates
    assert len(severities) == len(set(severities))
    
    # Verify the list is sorted
    assert severities == sorted(severities)
    
    # Print some debug info
    print(f"\nFound {len(severities)} unique severity levels")
    if severities:
        print(f"Available severities: {severities}") 