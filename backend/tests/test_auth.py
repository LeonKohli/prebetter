"""
Tests for authentication endpoints.
"""

from app.core.config import get_settings
from .conftest import TEST_USER

settings = get_settings()


def test_login_success(client, test_db):
    """Test successful login flow."""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
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
        data={"username": TEST_USER["username"], "password": "wrongpassword"},
    )
    assert response.status_code == 401
    # Non-existent user
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "nonexistentuser", "password": TEST_USER["password"]},
    )
    assert response.status_code == 401
    # Missing credentials
    response = client.post("/api/v1/auth/token")
    assert response.status_code == 422
    # Malformed request (JSON instead of form data)
    response = client.post(
        "/api/v1/auth/token",
        json={"username": TEST_USER["username"], "password": TEST_USER["password"]},
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
        "/api/v1/reference/classifications",
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


def test_login_returns_token_pair(client, test_db):
    """Test that login returns both access and refresh tokens with correct fields."""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify complete token response structure
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data
    assert "expires_in" in data

    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_refresh_token_flow(client, test_db):
    """Test the complete refresh token flow."""
    # Login to get tokens
    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()

    # Use refresh token to get new access token
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()

    # Verify new tokens structure
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert "expires_in" in new_tokens
    assert new_tokens["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # New access token should work
    headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    me_response = client.get("/api/v1/auth/users/me", headers=headers)
    assert me_response.status_code == 200


def test_refresh_token_rejected_as_access_token(client, test_db):
    """Test that refresh tokens cannot be used to access protected endpoints."""
    # Login to get tokens
    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
    )
    tokens = login_response.json()

    # Try to use refresh token as Bearer token - MUST fail
    headers = {"Authorization": f"Bearer {tokens['refresh_token']}"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401, "Refresh token should NOT work as access token"


def test_access_token_rejected_for_refresh(client, test_db):
    """Test that access tokens cannot be used to refresh."""
    # Login to get tokens
    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
    )
    tokens = login_response.json()

    # Try to use access token for refresh - MUST fail
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )
    assert refresh_response.status_code == 401, "Access token should NOT work for refresh"


def test_invalid_refresh_token(client, test_db):
    """Test that invalid refresh tokens are rejected."""
    # Malformed token
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )
    assert response.status_code == 401

    # Empty token
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": ""},
    )
    assert response.status_code == 401
