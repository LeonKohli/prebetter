"""
Test fixtures with dual-database transaction rollback isolation.

Both Prelude (IDS data) and Prebetter (users) databases are wrapped in
transactions that rollback after each test - no real data is ever modified.
"""

import pytest
import uuid
from collections.abc import Generator
from pathlib import Path
from dotenv import load_dotenv

# Load .env.test BEFORE importing app
env_file = Path(__file__).parent.parent / ".env.test"
load_dotenv(env_file)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.main import app
from app.models.users import User
from app.core.security import get_password_hash
from app.core.config import get_settings
from app.database.config import get_prebetter_db, get_prelude_db


# Test data
TEST_USER = {
    "username": "testuser",
    "password": "testpassword",
    "email": "test@example.com",
}

TEST_SUPERUSER = {
    "username": "admin",
    "password": "admin",
    "email": "admin@example.com",
    "full_name": "Admin User",
}


# =============================================================================
# Database Engines and Connections (session-scoped)
# =============================================================================


@pytest.fixture(scope="session")
def prebetter_db_engine():
    """Prebetter database engine - created once per test session."""
    settings = get_settings()
    engine = create_engine(settings.PREBETTER_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def prelude_db_engine():
    """Prelude database engine - created once per test session."""
    settings = get_settings()
    engine = create_engine(settings.PRELUDE_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def prebetter_db_connection(prebetter_db_engine):
    """Single Prebetter connection reused across all tests."""
    connection = prebetter_db_engine.connect()
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def prelude_db_connection(prelude_db_engine):
    """Single Prelude connection reused across all tests."""
    connection = prelude_db_engine.connect()
    yield connection
    connection.close()


# =============================================================================
# Database Sessions with Transaction Rollback (function-scoped)
# =============================================================================


@pytest.fixture(scope="function")
def test_db(prebetter_db_connection) -> Generator[Session, None, None]:
    """Prebetter DB session - sets up users, rolls back after test."""
    transaction = prebetter_db_connection.begin()
    session = Session(
        bind=prebetter_db_connection, join_transaction_mode="create_savepoint"
    )

    def override():
        yield session

    app.dependency_overrides[get_prebetter_db] = override

    # Setup admin
    admin = session.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            id=str(uuid.uuid4()),
            username=TEST_SUPERUSER["username"],
            email=TEST_SUPERUSER["email"],
            full_name=TEST_SUPERUSER["full_name"],
            hashed_password=get_password_hash(TEST_SUPERUSER["password"]),
            is_superuser=True,
        )
        session.add(admin)
    else:
        admin.hashed_password = get_password_hash(TEST_SUPERUSER["password"])
        admin.is_superuser = True
    session.flush()

    # Setup test user
    test_user = User(
        id=str(uuid.uuid4()),
        email=TEST_USER["email"],
        username=TEST_USER["username"],
        hashed_password=get_password_hash(TEST_USER["password"]),
    )
    session.add(test_user)
    session.flush()

    yield session

    session.close()
    transaction.rollback()
    app.dependency_overrides.pop(get_prebetter_db, None)


@pytest.fixture(scope="function")
def prelude_test_db(prelude_db_connection) -> Generator[Session, None, None]:
    """Prelude DB session - any operation (including DELETE) rolls back after test."""
    transaction = prelude_db_connection.begin()
    session = Session(
        bind=prelude_db_connection, join_transaction_mode="create_savepoint"
    )

    def override():
        yield session

    app.dependency_overrides[get_prelude_db] = override

    yield session

    session.close()
    transaction.rollback()
    app.dependency_overrides.pop(get_prelude_db, None)


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest.fixture
def client(prelude_db_engine) -> TestClient:
    """TestClient for the FastAPI app.

    Sets up app.state.pair_table since TestClient doesn't trigger lifespan
    without using `with` statement (which we can't use for fixture-based testing).
    """
    from app.repositories.alerts import reflect_pair_table

    # Reflect pair_table and set on app.state (normally done in lifespan)
    app.state.pair_table = reflect_pair_table(prelude_db_engine)

    return TestClient(app)


@pytest.fixture
def auth_token(client: TestClient, test_db: Session, prelude_test_db: Session) -> str:
    """JWT token for test user. Both DBs isolated via fixture deps."""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": TEST_USER["username"], "password": TEST_USER["password"]},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_client(client: TestClient, auth_token: str) -> TestClient:
    """Authenticated TestClient for regular user."""
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


@pytest.fixture
def superuser(test_db: Session) -> User:
    """The superuser from test database."""
    return test_db.query(User).filter(User.username == TEST_SUPERUSER["username"]).one()


@pytest.fixture
def superuser_token(
    client: TestClient, test_db: Session, prelude_test_db: Session, superuser: User
) -> str:
    """JWT token for superuser. Both DBs isolated via fixture deps."""
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
    """Authenticated TestClient for superuser."""
    client.headers["Authorization"] = f"Bearer {superuser_token}"
    return client
