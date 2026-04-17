from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentSuperuser, CurrentUser, UserServiceDep
from app.models.users import User
from app.schemas.filters import PaginationParams
from app.schemas.prelude import PaginatedResponse
from app.schemas.users import (
    PasswordChangeRequest,
    PasswordResetRequest,
    PaginatedUserResponse,
    User as UserSchema,
    UserCreate,
    UserUpdate,
)

router = APIRouter()


@router.post("/", response_model=UserSchema)
def create_user(
    user: UserCreate,
    current_user: CurrentSuperuser,
    user_service: UserServiceDep,
) -> User:
    """
    Create a new user (accessible by superusers only).
    """
    return user_service.create_user(user)


@router.get("/", response_model=PaginatedUserResponse)
def list_users(
    current_user: CurrentSuperuser,
    user_service: UserServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
) -> PaginatedUserResponse:
    """
    List all users with pagination (superusers only).
    Returns a standardized paginated response.
    """
    total_users = user_service.count_users()
    users = user_service.list_users(skip=pagination.offset, limit=pagination.size)

    return PaginatedUserResponse(
        items=[UserSchema.model_validate(user) for user in users],
        pagination=PaginatedResponse(
            total=total_users,
            page=pagination.page,
            size=pagination.size,
            pages=pagination.total_pages(total_users),
        ),
    )


@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: str,
    current_user: CurrentSuperuser,
    user_service: UserServiceDep,
) -> User:
    """
    Retrieve details for a specific user by user_id (superusers only).
    """
    user = user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: CurrentSuperuser,
    user_service: UserServiceDep,
) -> User:
    """
    Update a user's details (superusers only).
    """
    return user_service.update_user(user_id, user_update)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current_user: CurrentSuperuser,
    user_service: UserServiceDep,
) -> None:
    """
    Delete a user by user_id (superusers only).
    """
    user_service.delete_user(user_id)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser,
    user_service: UserServiceDep,
) -> None:
    """
    Allow any authenticated user to change their own password.
    """
    user_service.change_password(current_user, payload)


@router.post("/{user_id}/reset-password", response_model=UserSchema)
def reset_user_password(
    user_id: str,
    payload: PasswordResetRequest,
    current_user: CurrentSuperuser,
    user_service: UserServiceDep,
) -> User:
    """
    Reset a user's password (accessible by superusers only).
    """
    return user_service.reset_password(user_id, payload)
