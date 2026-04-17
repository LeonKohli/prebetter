from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from pydantic import ConfigDict
from app.schemas.prelude import PaginatedResponse

# Field length constraints (must match frontend validation.ts)
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50
FULL_NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 255  # DB limit
PASSWORD_MIN_LENGTH = 8
# bcrypt silently truncates at 72 bytes (<=4.x) or raises ValueError (>=5.x).
# Enforce the limit at the API boundary so behavior is stable across versions
# and multibyte passwords (e.g. emoji) get a clean 422 instead of a 500.
PASSWORD_MAX_BYTES = 72


def _validate_non_empty_string(v: str | None) -> str | None:
    """Shared validator for non-empty string fields."""
    if v is not None and not v.strip():
        raise ValueError("Field cannot be empty or whitespace only")
    return v


def _validate_password_bytes(v: str | None) -> str | None:
    """Reject passwords exceeding bcrypt's 72-byte limit (UTF-8 encoded)."""
    if v is not None and len(v.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(
            f"Password must be at most {PASSWORD_MAX_BYTES} bytes when UTF-8 encoded"
        )
    return v


class UserBase(BaseModel):
    email: EmailStr = Field(max_length=EMAIL_MAX_LENGTH)
    username: str = Field(
        min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH
    )
    full_name: str | None = Field(default=None, max_length=FULL_NAME_MAX_LENGTH)

    @field_validator("username", "full_name")
    @classmethod
    def validate_non_empty_string(cls, v: str | None) -> str | None:
        return _validate_non_empty_string(v)


class UserCreate(UserBase):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)
    is_superuser: bool = False

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_bytes(v)  # type: ignore[return-value]


class UserUpdate(BaseModel):
    username: str | None = Field(
        default=None, min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH
    )
    email: EmailStr | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    full_name: str | None = Field(default=None, max_length=FULL_NAME_MAX_LENGTH)
    password: str | None = Field(default=None, min_length=PASSWORD_MIN_LENGTH)
    is_superuser: bool | None = None

    @field_validator("username", "full_name")
    @classmethod
    def validate_non_empty_string(cls, v: str | None) -> str | None:
        return _validate_non_empty_string(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        return _validate_password_bytes(v)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_bytes(v)  # type: ignore[return-value]


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_bytes(v)  # type: ignore[return-value]


class UserInDBBase(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime | None = None
    is_superuser: bool = False

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    """
    Schema for returning user data.
    """

    pass


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
    items: list[User]
    pagination: PaginatedResponse

    model_config = ConfigDict(from_attributes=True)
