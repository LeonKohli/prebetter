"""Verify the JWKS-based token verification in app.api.deps.

Generates a local Ed25519 keypair, signs tokens like Better Auth would, and
patches the module's JWKS client to return the matching public key - no network.
"""

import jwt
import pytest
from datetime import timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import app.api.deps as deps
from app.core.datetime_utils import get_current_time

ISSUER = deps.settings.BETTER_AUTH_URL


@pytest.fixture(scope="module")
def keypair():
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    return private_pem, public_key


@pytest.fixture(autouse=True)
def patch_jwks(monkeypatch, keypair):
    _, public_key = keypair

    class _SigningKey:
        key = public_key

    monkeypatch.setattr(
        deps._jwks_client, "get_signing_key_from_jwt", lambda token: _SigningKey()
    )


def make_token(
    private_pem,
    *,
    sub="user-123",
    role="user",
    exp_delta=timedelta(minutes=15),
    issuer=ISSUER,
    audience=ISSUER,
    extra=None,
):
    now = get_current_time()
    payload = {
        "sub": sub,
        "role": role,
        "username": "alice",
        "email": "alice@example.com",
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + exp_delta,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, private_pem, algorithm="EdDSA")


def creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_valid_token_returns_identity(keypair):
    private_pem, _ = keypair
    user = deps.get_current_user(creds(make_token(private_pem, role="admin")))
    assert user.id == "user-123"
    assert user.username == "alice"
    assert user.role == "admin"


def test_expired_token_rejected(keypair):
    private_pem, _ = keypair
    token = make_token(private_pem, exp_delta=timedelta(minutes=-1))
    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(creds(token))
    assert exc.value.status_code == 401


def test_wrong_issuer_rejected(keypair):
    private_pem, _ = keypair
    token = make_token(private_pem, issuer="https://evil.example.com")
    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(creds(token))
    assert exc.value.status_code == 401


def test_wrong_audience_rejected(keypair):
    private_pem, _ = keypair
    token = make_token(private_pem, audience="https://other.example.com")
    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(creds(token))
    assert exc.value.status_code == 401


def test_missing_subject_rejected(keypair):
    private_pem, _ = keypair
    token = make_token(private_pem, sub="")
    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(creds(token))
    assert exc.value.status_code == 401


def test_superuser_requires_admin_role():
    admin = deps.AuthUser(id="1", role="admin")
    assert deps.get_current_superuser(admin) is admin

    regular = deps.AuthUser(id="2", role="user")
    with pytest.raises(HTTPException) as exc:
        deps.get_current_superuser(regular)
    assert exc.value.status_code == 403
