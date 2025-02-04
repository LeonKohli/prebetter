"""
Tests for authentication endpoints.
"""

from .conftest import TEST_USER

def test_login_success(client, test_db):
    """Test successful login flow."""
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    # Verify token structure
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    # Verify token works by accessing a protected endpoint
    auth_headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_response = client.get("/api/v1/auth/users/me", headers=auth_headers)
    assert me_response.status_code == 200
    user_data = me_response.json()
    assert user_data["username"] == TEST_USER["username"]
    assert user_data["email"] == TEST_USER["email"]

def test_login_failures(client, test_db):
    """Test various login failure scenarios."""
    # Wrong password
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": TEST_USER["username"],
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    # Non-existent user
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": "nonexistentuser",
            "password": TEST_USER["password"]
        }
    )
    assert response.status_code == 401
    # Missing credentials
    response = client.post("/api/v1/auth/token")
    assert response.status_code == 422
    # Malformed request (JSON instead of form data)
    response = client.post(
        "/api/v1/auth/token",
        json={"username": TEST_USER["username"], "password": TEST_USER["password"]}
    )
    assert response.status_code == 422

def test_protected_endpoints_without_auth(client, test_db):
    """Test accessing protected endpoints without authentication"""
    # Test /users/me endpoint
    response = client.get("/api/v1/auth/users/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]
    
    # Test other protected endpoints
    endpoints = [
        "/api/v1/alerts/",
        "/api/v1/statistics/summary",
        "/api/v1/classifications"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

def test_invalid_tokens(client, test_db):
    """Test various invalid token scenarios"""
    # Test with malformed token
    headers = {"Authorization": "Bearer malformedtoken"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401
    
    # Test with wrong token format
    headers = {"Authorization": "malformedtoken"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401
    
    # Test with empty token
    headers = {"Authorization": "Bearer "}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401
    
    # Test with invalid bearer prefix
    headers = {"Authorization": "Basic sometoken"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401 