from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional, List
from pydantic import ConfigDict
from app.schemas.prelude import PaginatedResponse


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    is_superuser: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_superuser: Optional[bool] = None

    @field_validator("username", "full_name")
    @classmethod
    def validate_non_empty_string(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v


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
    token_type: str


class TokenData(BaseModel):
    user_id: str


class PaginatedUserResponse(BaseModel):
    items: List[User]
    pagination: PaginatedResponse

    model_config = ConfigDict(from_attributes=True)
