from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.security import ALGORITHM, SECRET_KEY
from app.database.config import get_prebetter_db
from app.models.users import User
from app.schemas.users import TokenData
from app.services.users import UserService

# OAuth2 configuration for Swagger UI "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
TokenDep = Annotated[str, Depends(oauth2_scheme)]


def get_user_service(
    db: Annotated[Session, Depends(get_prebetter_db, scope="function")],
) -> UserService:
    return UserService(db)


UserServiceDep = Annotated[
    UserService,
    Depends(get_user_service, scope="function"),
]


def validate_access_token(token: str, user_service: UserService) -> User:
    """Validate an access token and return the associated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Reject refresh tokens used as access tokens.
        if payload.get("type") != "access":
            raise credentials_exception

        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except PyJWTError:
        raise credentials_exception

    user = user_service.get_by_id(token_data.user_id)
    if not user:
        raise credentials_exception
    return user


def get_current_user(
    token: TokenDep,
    user_service: UserServiceDep,
) -> User:
    """Retrieve the current user based on JWT token."""
    return validate_access_token(token, user_service)


CurrentUser = Annotated[User, Depends(get_current_user, scope="function")]


def get_current_superuser(current_user: CurrentUser) -> User:
    """Ensure the current user is a superuser."""
    if current_user.is_superuser is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    return current_user


CurrentSuperuser = Annotated[
    User,
    Depends(get_current_superuser, scope="function"),
]
