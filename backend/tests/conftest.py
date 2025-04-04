import pytest
import uuid
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.users import User
from app.core.security import get_password_hash

# Global test data
TEST_USER = {
    "username": "testuser",
    "password": "testpassword",
    "email": "test@example.com"
}

TEST_SUPERUSER = {
    "username": "admin",
    "password": "admin",  # Must match what you have in your initialization (init_db.py)
    "email": "admin@example.com",
    "full_name": "Admin User"
}

@pytest.fixture
def client() -> TestClient:
    """Return a TestClient instance for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def test_db() -> Generator[Session, None, None]:
    """
    Provide a SQLAlchemy session with a clean test user database.
    This fixture cleans up non-admin users before and after each test.
    """
    from app.database.config import get_prebetter_db

    db = next(get_prebetter_db())

    # Clean up: Remove all users except admin before test
    db.query(User).filter(User.username != "admin").delete(synchronize_session=False)
    db.commit()

    # Ensure admin exists with correct password and superuser status
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        admin.hashed_password = get_password_hash("admin")
        admin.is_superuser = True
        db.commit()
        db.refresh(admin)
    else:
        # Optionally, create an admin if not exists (depending on your init logic)
        admin = User(
            id=str(uuid.uuid4()),
            username=TEST_SUPERUSER["username"],
            email=TEST_SUPERUSER["email"],
            full_name=TEST_SUPERUSER["full_name"],
            hashed_password=get_password_hash(TEST_SUPERUSER["password"]),
            is_superuser=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

    # Create the test user
    test_user = User(
        id=str(uuid.uuid4()),
        email=TEST_USER["email"],
        username=TEST_USER["username"],
        hashed_password=get_password_hash(TEST_USER["password"])
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    yield db

    # Clean up after tests: Remove all non-admin users
    db.query(User).filter(User.username != "admin").delete(synchronize_session=False)
    db.commit()
    
    # Reset admin to original state
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        admin.hashed_password = get_password_hash("admin")
        admin.is_superuser = True
        db.commit()

@pytest.fixture
def auth_token(client: TestClient, test_db: Session) -> str:
    """Log in as the test user and return the JWT access token."""
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
def auth_client(client: TestClient, auth_token: str) -> TestClient:
    """Return a TestClient instance with the Authorization header set for a regular user."""
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client

@pytest.fixture
def superuser(test_db: Session) -> User:
    """
    Ensure a superuser exists in the database and return the user.
    If the superuser already exists, update its password hash.
    """
    db = test_db
    existing = db.query(User).filter(User.username == TEST_SUPERUSER["username"]).first()
    if existing:
        existing.hashed_password = get_password_hash(TEST_SUPERUSER["password"])
        db.commit()
        db.refresh(existing)
        return existing

    # Create superuser if it does not exist
    user = User(
        id=str(uuid.uuid4()),
        username=TEST_SUPERUSER["username"],
        email=TEST_SUPERUSER["email"],
        full_name=TEST_SUPERUSER["full_name"],
        hashed_password=get_password_hash(TEST_SUPERUSER["password"]),
        is_superuser=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def superuser_token(client: TestClient, superuser: User) -> str:
    """Log in as the superuser and return the JWT access token."""
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": TEST_SUPERUSER["username"],
            "password": TEST_SUPERUSER["password"],
        },
    )
    assert response.status_code == 200, f"Token creation failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture
def superuser_client(client: TestClient, superuser_token: str) -> TestClient:
    """Return a TestClient instance with the Authorization header set for a superuser."""
    client.headers["Authorization"] = f"Bearer {superuser_token}"
    return client 