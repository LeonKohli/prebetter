from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from ..models.users import User
from ..schemas.users import UserCreate, UserUpdate, PasswordChangeRequest, PasswordResetRequest
from ..core.security import get_password_hash, verify_password, create_user_id
from sqlalchemy.exc import IntegrityError

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check for existing username or email
        if self.get_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        if self.get_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        db_user = User(
            id=create_user_id(),
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            is_superuser=False  # Only the first user can be superuser
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def update_user(self, user_id: str, user_update: UserUpdate) -> User:
        """Update a user's details."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user fields
        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(db_user)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        
        return db_user
    
    def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent deleting the last superuser
        if db_user.is_superuser:
            superuser_count = self.db.query(User).filter(User.is_superuser).count()
            if superuser_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last superuser"
                )
        
        self.db.delete(db_user)
        self.db.commit()
    
    def change_password(self, user: User, password_change: PasswordChangeRequest) -> None:
        """Change a user's password."""
        if not verify_password(password_change.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )
        
        user.hashed_password = get_password_hash(password_change.new_password)
        self.db.commit()
    
    def reset_password(self, user_id: str, password_reset: PasswordResetRequest) -> User:
        """Reset a user's password (admin only)."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        db_user.hashed_password = get_password_hash(password_reset.new_password)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user 