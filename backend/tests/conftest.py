import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI app that can be shared across all tests"""
    return TestClient(app) 