"""
Test fixtures with Prelude transaction-rollback isolation.

Prelude (IDS data) is wrapped in a transaction that rolls back after the test
session - no real data is modified. Authentication is stubbed via FastAPI
dependency overrides; the real JWKS verification path is covered in
test_auth_jwks.py.
"""

import pytest
from collections.abc import Generator
from pathlib import Path
from dotenv import load_dotenv
from tests.seed_prelude import seed_prelude_data

# Load .env.test BEFORE importing app modules (they read env vars at import time)
env_file = Path(__file__).parent.parent / ".env.test"
load_dotenv(env_file)

from app.scripts.prelude_pair_accelerator import CREATE_TABLE_SQL
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.main import app
from app.api.deps import AuthUser, get_current_user, get_current_superuser
from app.core.config import get_settings
from app.database.config import get_prelude_db


# Stubbed identities for route tests (real verification is in test_auth_jwks.py).
REGULAR_USER = AuthUser(
    id="test-user-id", username="testuser", email="test@example.com", role="user"
)
ADMIN_USER = AuthUser(
    id="admin-user-id", username="admin", email="admin@example.com", role="admin"
)


# =============================================================================
# Database Engines and Connections (session-scoped)
# =============================================================================


@pytest.fixture(scope="session")
def prelude_db_engine():
    """Prelude database engine - created once per test session."""
    settings = get_settings()
    engine = create_engine(settings.PRELUDE_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def prelude_db_connection(prelude_db_engine):
    """Single Prelude connection with seed data, reused across all tests.

    Creates the Prebetter_Pair table (DDL, auto-commits), then seeds all
    test data within a transaction that rolls back after the test session.
    """
    connection = prelude_db_engine.connect()

    # DDL: ensure Prebetter_Pair table exists (auto-commits in MySQL)
    connection.execute(text(CREATE_TABLE_SQL))
    connection.commit()

    # Seed test data within a transaction (rolls back after all tests)
    transaction = connection.begin()
    seed_prelude_data(connection)

    yield connection

    transaction.rollback()
    connection.close()


# =============================================================================
# Database Sessions with Transaction Rollback (function-scoped)
# =============================================================================


@pytest.fixture(scope="function")
def prelude_test_db(prelude_db_connection) -> Generator[Session, None, None]:
    """Prelude DB session with seed data. Savepoint rolls back after each test."""
    savepoint = prelude_db_connection.begin_nested()
    session = Session(
        bind=prelude_db_connection, join_transaction_mode="create_savepoint"
    )

    def override():
        yield session

    app.dependency_overrides[get_prelude_db] = override

    yield session

    session.close()
    savepoint.rollback()
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
def auth_client(
    client: TestClient, prelude_test_db: Session
) -> Generator[TestClient, None, None]:
    """TestClient authenticated as a regular user via dependency override."""
    app.dependency_overrides[get_current_user] = lambda: REGULAR_USER
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def superuser_client(
    client: TestClient, prelude_test_db: Session
) -> Generator[TestClient, None, None]:
    """TestClient authenticated as an admin via dependency override."""
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER
    app.dependency_overrides[get_current_superuser] = lambda: ADMIN_USER
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_superuser, None)
