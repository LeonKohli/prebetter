from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Annotated
from app.database.config import get_prebetter_db
from app.models.users import User
from app.schemas.users import (
    UserCreate,
    UserUpdate,
    User as UserSchema,
    PasswordChangeRequest,
    PasswordResetRequest,
)
from app.api.v1.routes.auth import get_current_user
from app.services.users import UserService

router = APIRouter()


def get_user_service(db: Session = Depends(get_prebetter_db)) -> UserService:
    """Dependency to get a UserService instance."""
    return UserService(db)


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Ensure the current user is a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user


@router.post("/", response_model=UserSchema)
async def create_user(
    user: UserCreate,
    current_user: Annotated[User, Depends(get_current_superuser)],
    user_service: UserService = Depends(get_user_service)
) -> User:
    """
    Create a new user (accessible by superusers only).
    """
    return user_service.create_user(user)


@router.get("/", response_model=List[UserSchema])
async def list_users(
    current_user: Annotated[User, Depends(get_current_superuser)],
    user_service: UserService = Depends(get_user_service),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
) -> List[User]:
    """
    List all users with pagination (superusers only).
    Uses page and size for pagination.
    """
    skip = (page - 1) * size
    return user_service.list_users(skip=skip, limit=size)


@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: str,
    current_user: Annotated[User, Depends(get_current_superuser)],
    user_service: UserService = Depends(get_user_service)
) -> User:
    """
    Retrieve details for a specific user by user_id (superusers only).
    """
    user = user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_superuser)],
    user_service: UserService = Depends(get_user_service)
) -> User:
    """
    Update a user's details (superusers only).
    """
    return user_service.update_user(user_id, user_update)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: Annotated[User, Depends(get_current_superuser)],
    user_service: UserService = Depends(get_user_service)
) -> None:
    """
    Delete a user by user_id (superusers only).
    """
    user_service.delete_user(user_id)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserService = Depends(get_user_service)
) -> None:
    """
    Allow any authenticated user to change their own password.
    """
    user_service.change_password(current_user, payload)


@router.post("/{user_id}/reset-password", response_model=UserSchema)
async def reset_user_password(
    user_id: str,
    payload: PasswordResetRequest,
    current_user: Annotated[User, Depends(get_current_superuser)],
    user_service: UserService = Depends(get_user_service)
) -> User:
    """
    Reset a user's password (accessible by superusers only).
    """
    return user_service.reset_password(user_id, payload)
