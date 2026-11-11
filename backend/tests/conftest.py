"""
Fixtures for tests against a real OpenSearch node (see compose.opensearch.yml).

The node's address and index pattern come from the environment or `.env.test`.
Authentication is stubbed through dependency overrides; the real JWKS verification
is covered in test_auth_jwks.py.
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env.test BEFORE importing app modules (they read the settings at import time)
load_dotenv(Path(__file__).parent.parent / ".env.test")

from fastapi.testclient import TestClient
from opensearchpy import OpenSearch

from app.api.deps import AuthUser, get_current_user
from app.core.config import get_settings
from app.main import app
from tests.seed import seed

TEST_INDEX_PREFIX = "prebetter-test-"

REGULAR_USER = AuthUser(
    id="test-user-id", username="testuser", email="test@example.com", role="user"
)


@pytest.fixture(scope="session", autouse=True)
def seeded_indices() -> Generator[list[str]]:
    """Seed the test indices once; refuse to run against anything but a test pattern."""
    settings = get_settings()
    patterns = [settings.OPENSEARCH_INDEX, settings.OPENSEARCH_REQUEST_INDEX]
    if not all(p.startswith(TEST_INDEX_PREFIX) for p in patterns):
        pytest.exit(
            "OPENSEARCH_INDEX and OPENSEARCH_REQUEST_INDEX must start with "
            f"{TEST_INDEX_PREFIX!r} to run the tests, got {patterns!r}",
            returncode=2,
        )
    client = OpenSearch(hosts=[settings.OPENSEARCH_URL])
    # Leftovers of an aborted run would make index creation fail.
    client.indices.delete(index=patterns, params={"ignore_unavailable": "true"})
    indices = seed(client, settings.OPENSEARCH_INDEX, settings.OPENSEARCH_REQUEST_INDEX)
    yield indices
    client.indices.delete(index=indices)
    client.close()


@pytest.fixture(scope="session")
def client() -> Generator[TestClient]:
    """App with its lifespan running, so it owns a real OpenSearch client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def api(client: TestClient) -> Generator[TestClient]:
    """The same client, authenticated as a regular user."""
    app.dependency_overrides[get_current_user] = lambda: REGULAR_USER
    yield client
    app.dependency_overrides.pop(get_current_user, None)
