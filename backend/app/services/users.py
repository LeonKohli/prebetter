from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.users import User
from app.schemas.users import (
    UserCreate,
    UserUpdate,
    PasswordChangeRequest,
    PasswordResetRequest,
)
from app.core.security import get_password_hash, verify_password, create_user_id
from sqlalchemy.exc import IntegrityError


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve a user by their ID."""
        return self.db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

    def get_by_username(self, username: str) -> Optional[User]:
        """Retrieve a user by their username."""
        return self.db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by their email."""
        return self.db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with pagination."""
        return list(self.db.scalars(select(User).offset(skip).limit(limit)).all())

    def count_users(self) -> int:
        """Count the total number of users."""
        return self.db.scalar(select(func.count(User.id))) or 0

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        if self.get_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
        if self.get_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists",
            )

        db_user = User(
            id=create_user_id(),
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            is_superuser=getattr(user_data, "is_superuser", False),
        )
        self.db.add(db_user)
        try:
            self.db.commit()
            self.db.refresh(db_user)
        except IntegrityError:
            # Race condition - user created between check and insert
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists",
            )
        return db_user

    def update_user(self, user_id: str, user_update: UserUpdate) -> User:
        """Update an existing user's details."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )

        for field, value in update_data.items():
            setattr(db_user, field, value)

        try:
            self.db.commit()
            self.db.refresh(db_user)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists",
            )

        return db_user

    def delete_user(self, user_id: str) -> None:
        """Delete a user by their ID."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Prevent deleting last superuser (administrative lockout)
        if db_user.is_superuser is True:
            superuser_count = (
                self.db.scalar(
                    select(func.count(User.id)).where(User.is_superuser == True)  # noqa: E712
                )
                or 0
            )
            if superuser_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last superuser",
                )

        self.db.delete(db_user)
        self.db.commit()

    def change_password(
        self, user: User, password_change: PasswordChangeRequest
    ) -> None:
        """Change the password for the current user."""
        if not verify_password(
            password_change.current_password, str(user.hashed_password)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password",
            )

        user.hashed_password = get_password_hash(password_change.new_password)
        self.db.commit()

    def reset_password(
        self, user_id: str, password_reset: PasswordResetRequest
    ) -> User:
        """Reset a user's password (admin only)."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        db_user.hashed_password = get_password_hash(password_reset.new_password)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
