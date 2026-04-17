from datetime import timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt import PyJWTError

from app.api.deps import CurrentUser, UserServiceDep
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.models.users import User
from app.schemas.users import (
    Token,
    RefreshRequest,
    User as UserSchema,
    UserUpdate,
)
from app.services.users import UserService

router = APIRouter()


def authenticate_user(
    user_service: UserService, username: str, password: str
) -> User | None:
    """Authenticate a user given username and password."""
    user = user_service.get_by_username(username)
    if not user:
        return None
    if not verify_password(password, str(user.hashed_password)):
        return None
    return user


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserServiceDep,
) -> Token:
    """Authenticate user and return access + refresh token pair."""
    user = authenticate_user(user_service, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    refresh_data: RefreshRequest,
    user_service: UserServiceDep,
) -> Token:
    """Exchange valid refresh token for new access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            refresh_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    # Verify user still exists
    user = user_service.get_by_id(user_id)
    if not user:
        raise credentials_exception

    # Issue new access token, keep same refresh token
    # Note: Stateless rotation without DB tracking is security theater.
    # For internal tools with server-side sessions, reusing the refresh token
    # is simpler and equally secure - the Nuxt session IS the refresh mechanism.
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return Token(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/users/me", response_model=UserSchema)
def read_users_me(current_user: CurrentUser) -> User:
    """Retrieve authenticated user profile."""
    return current_user


@router.put("/users/me", response_model=UserSchema)
def update_profile(
    profile_update: UserUpdate,
    current_user: CurrentUser,
    user_service: UserServiceDep,
) -> User:
    """Update authenticated user profile (excluding password and privileges)."""
    # Prevent privilege escalation
    update_data = profile_update.model_dump(exclude_unset=True)
    if "is_superuser" in update_data:
        del update_data["is_superuser"]
    if "password" in update_data:
        del update_data["password"]
    filtered_update = UserUpdate(**update_data)

    return user_service.update_user(str(current_user.id), filtered_update)
