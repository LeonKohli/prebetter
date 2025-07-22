from datetime import timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import jwt
from jwt import PyJWTError

from app.core.security import (
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.database.config import get_prebetter_db
from app.models.users import User
from app.schemas.users import Token, TokenData, User as UserSchema, UserUpdate
from app.services.users import UserService

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_user_service(db: Session = Depends(get_prebetter_db)) -> UserService:
    """Dependency to get a UserService instance."""
    return UserService(db)


def authenticate_user(
    user_service: UserService, username: str, password: str
) -> Optional[User]:
    """
    Authenticate a user given a username and password.
    Returns the user if authentication is successful; otherwise, returns None.
    """
    user = user_service.get_by_username(username)
    if not user:
        return None
    if not verify_password(password, str(user.hashed_password)):
        return None
    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: UserService = Depends(get_user_service),
) -> User:
    """
    Retrieve the current user based on the provided JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserService = Depends(get_user_service),
) -> Token:
    """
    Authenticate the user and return an access token.
    """
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
    return Token(access_token=access_token, token_type="bearer")


@router.get("/users/me", response_model=UserSchema)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Retrieve the profile of the authenticated user.
    """
    return current_user


@router.put("/users/me", response_model=UserSchema)
async def update_profile(
    profile_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserService = Depends(get_user_service),
) -> User:
    """
    Update the profile of the authenticated user.
    Users can update their username, email, and full name.
    Password updates should use the change-password endpoint.
    """
    # Prevent regular users from changing their superuser status
    update_data = profile_update.model_dump(exclude_unset=True)
    if "is_superuser" in update_data:
        del update_data["is_superuser"]
    
    # Remove password from profile update (use change-password endpoint instead)
    if "password" in update_data:
        del update_data["password"]
    
    # Create a new UserUpdate instance with filtered data
    filtered_update = UserUpdate(**update_data)
    
    return user_service.update_user(str(current_user.id), filtered_update)
