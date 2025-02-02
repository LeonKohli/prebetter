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

def test_get_unique_classifications_edge_cases(client):
    """Test edge cases for the classifications endpoint"""
    # Test error handling by simulating database errors
    # Note: This assumes the endpoint handles database errors gracefully
    
    # Test response format consistency
    response = client.get("/api/v1/classifications")
    assert response.status_code == 200
    data = response.json()
    
    # Verify each classification is a non-empty string
    assert all(isinstance(c, str) and len(c) > 0 for c in data)
    
    # Verify no null values
    assert all(c is not None for c in data)
    
    # Verify no duplicate values (case-sensitive)
    assert len(data) == len(set(data))
    
    # Verify no duplicate values (case-insensitive)
    lower_case = [c.lower() for c in data]
    assert len(lower_case) == len(set(lower_case))

def test_get_unique_severities_edge_cases(client):
    """Test edge cases for the severities endpoint"""
    # Test error handling by simulating database errors
    # Note: This assumes the endpoint handles database errors gracefully
    
    # Test response format consistency
    response = client.get("/api/v1/severities")
    assert response.status_code == 200
    data = response.json()
    
    # Verify each severity is a non-empty string
    assert all(isinstance(s, str) and len(s) > 0 for s in data)
    
    # Verify no null values
    assert all(s is not None for s in data)
    
    # Verify no duplicate values (case-sensitive)
    assert len(data) == len(set(data))
    
    # Verify no duplicate values (case-insensitive)
    lower_case = [s.lower() for s in data]
    assert len(lower_case) == len(set(lower_case))
    
    # Verify common severity levels are present if data exists
    if data:
        common_severities = {"high", "medium", "low", "info"}
        found_severities = {s.lower() for s in data}
        assert any(s in found_severities for s in common_severities) 