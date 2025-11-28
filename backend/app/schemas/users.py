from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List
from pydantic import ConfigDict
from app.schemas.prelude import PaginatedResponse

# Field length constraints (must match frontend validation.ts)
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50
FULL_NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 255  # DB limit


def _validate_non_empty_string(v: Optional[str]) -> Optional[str]:
    """Shared validator for non-empty string fields."""
    if v is not None and not v.strip():
        raise ValueError("Field cannot be empty or whitespace only")
    return v


class UserBase(BaseModel):
    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH)
    username: str = Field(
        min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH
    )
    full_name: Optional[str] = Field(default=None, max_length=FULL_NAME_MAX_LENGTH)

    @field_validator("username", "full_name")
    @classmethod
    def validate_non_empty_string(cls, v: Optional[str]) -> Optional[str]:
        return _validate_non_empty_string(v)


class UserCreate(UserBase):
    password: str
    is_superuser: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = Field(
        default=None, min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH
    )
    email: Optional[EmailStr] = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    full_name: Optional[str] = Field(default=None, max_length=FULL_NAME_MAX_LENGTH)
    password: Optional[str] = None
    is_superuser: Optional[bool] = None

    @field_validator("username", "full_name")
    @classmethod
    def validate_non_empty_string(cls, v: Optional[str]) -> Optional[str]:
        return _validate_non_empty_string(v)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    new_password: str


class UserInDBBase(UserBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_superuser: bool = False

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    """
    Schema for returning user data.
    """

    pass


class UserInDB(UserInDBBase):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int  # Seconds until access token expires


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_id: str


class PaginatedUserResponse(BaseModel):
    items: List[User]
    pagination: PaginatedResponse

    model_config = ConfigDict(from_attributes=True)
