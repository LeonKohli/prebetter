from datetime import timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
import uuid
from .config import get_settings
from .datetime_utils import get_current_time

settings = get_settings()

# Security configuration using settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hashed version.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with expiration and issued-at claims.
    Includes microsecond precision to ensure unique tokens in rapid succession.
    """
    to_encode = data.copy()
    now = get_current_time()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": f"{now.timestamp()}-{uuid.uuid4()}"  # Add a unique token ID with timestamp and UUID
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_user_id() -> str:
    """
    Generate a unique user ID.
    """
    return str(uuid.uuid4())
