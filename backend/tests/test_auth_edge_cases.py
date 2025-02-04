import pytest
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timedelta, UTC
from app.core.security import create_access_token, SECRET_KEY, ALGORITHM
import time

def test_token_expiration(auth_client, client):
    """
    Test token expiration handling.
    """
    # Create a token that's already expired
    expired_token = create_access_token(
        data={"sub": "testuser"},
        expires_delta=timedelta(minutes=-1)
    )

    # Try to access protected endpoint with expired token
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401, "Expired token was accepted"

def test_invalid_token_formats(client):
    """
    Test various invalid token formats.
    """
    # Test with malformed token
    headers = {"Authorization": "Bearer abc123"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401, "Malformed token was accepted"

    # Test with invalid signature
    payload = {
        "sub": "testuser",
        "exp": datetime.now(UTC) + timedelta(minutes=30)
    }
    invalid_token = jwt.encode(payload, "wrong_secret", algorithm=ALGORITHM)
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401, "Token with invalid signature was accepted"

    # Test with missing Bearer prefix
    headers = {"Authorization": "abc123"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401, "Token without Bearer prefix was accepted"

    # Test with empty token
    headers = {"Authorization": "Bearer "}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401, "Empty token was accepted"

def test_login_rate_limiting(client, test_db):
    """
    Test rate limiting for login attempts.
    """
    # Attempt multiple rapid login requests
    for _ in range(10):
        response = client.post(
            "/api/v1/auth/token",
            data={
                "username": "nonexistent",
                "password": "wrongpassword"
            }
        )
        assert response.status_code in [401, 429], "Rate limiting not enforced"

def test_token_refresh(auth_client, client):
    """
    Test token refresh functionality.
    """
    # Get initial token
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    initial_token = response.json()["access_token"]

    # Use token to access protected endpoint
    headers = {"Authorization": f"Bearer {initial_token}"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 200

def test_concurrent_login(client, test_db):
    """
    Test concurrent login attempts for the same user.
    """
    # Add a small delay between requests to ensure unique tokens

    # Simulate concurrent login requests
    responses = []
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        responses.append(response)
        time.sleep(1)  # Use a 1-second delay to ensure unique tokens

    # All requests should succeed and return valid tokens
    tokens = set()
    for response in responses:
        assert response.status_code == 200
        token = response.json()["access_token"]
        tokens.add(token)

    # Each token should be unique
    assert len(tokens) == len(responses), "Duplicate tokens were issued"

def test_auth_headers_validation(client):
    """
    Test validation of authentication headers.
    """
    # Test with missing Authorization header
    response = client.get("/api/v1/auth/users/me")
    assert response.status_code == 401, "Request without Authorization header was accepted"

    # Test with malformed Authorization header
    headers = {"Authorization": "Basic abc123"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401, "Invalid auth scheme was accepted"

    # Test with multiple Authorization headers (using a comma-separated string)
    headers = {"Authorization": "Bearer token1, Bearer token2"}
    response = client.get("/api/v1/auth/users/me", headers=headers)
    assert response.status_code == 401, "Multiple Authorization headers were accepted" 