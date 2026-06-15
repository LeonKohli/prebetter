from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient, PyJWTError
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()

# JWKS client fetches and caches Better Auth's public keys.
_jwks_client = PyJWKClient(settings.JWKS_URL)

# Bearer scheme drives Swagger UI's "Authorize" button.
bearer_scheme = HTTPBearer(auto_error=True)
BearerDep = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]


class AuthUser(BaseModel):
    """Authenticated identity built from verified JWT claims (no DB lookup)."""

    id: str
    username: str | None = None
    email: str | None = None
    role: str | None = None


def get_current_user(credentials: BearerDep) -> AuthUser:
    """Verify a Better Auth JWT against its JWKS and return the identity."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(credentials.credentials)
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.BETTER_AUTH_URL,
            audience=settings.BETTER_AUTH_URL,
            leeway=15,  # tolerate small clock skew between Nuxt and the API
        )
    except PyJWTError:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    return AuthUser(
        id=user_id,
        username=payload.get("username"),
        email=payload.get("email"),
        role=payload.get("role"),
    )


CurrentUser = Annotated[AuthUser, Depends(get_current_user, scope="function")]


def get_current_superuser(current_user: CurrentUser) -> AuthUser:
    """Ensure the current user has the admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    return current_user


CurrentSuperuser = Annotated[
    AuthUser,
    Depends(get_current_superuser, scope="function"),
]
