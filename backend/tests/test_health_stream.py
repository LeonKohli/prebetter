"""Health, the 503 handler and the change stream."""

import asyncio
from collections.abc import Generator

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from starlette.types import Message
from opensearchpy import AsyncOpenSearch, OpenSearch

from app.api.deps import get_current_user
from app.api.v1.routes import alerts as alerts_routes
from app.core.config import get_settings
from app.main import app
from app.repositories.alerts import AlertRepository
from tests.conftest import REGULAR_USER
from tests.seed import TEST_BASE, build_event


def test_health_reports_a_reachable_node(client):
    body = client.get("/health").json()

    assert body["status"] == "healthy"
    assert body["opensearch"] is True


@pytest.fixture
def unreachable(client, monkeypatch) -> Generator[TestClient]:
    """App whose lifespan builds its client for a port nothing listens on."""
    working = app.state.opensearch
    monkeypatch.setattr(get_settings(), "OPENSEARCH_URL", "http://127.0.0.1:9")
    with TestClient(app) as test_client:
        yield test_client
    app.state.opensearch = working  # the session client keeps using its own


def test_health_is_unhealthy_without_a_node(unreachable):
    response = unreachable.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "unhealthy"
    assert response.json()["opensearch"] is False


def test_unreachable_node_answers_503(unreachable):
    app.dependency_overrides[get_current_user] = lambda: REGULAR_USER
    try:
        response = unreachable.get("/api/v1/alerts")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_stream_announces_new_documents(monkeypatch):
    monkeypatch.setattr(alerts_routes, "POLL_INTERVAL_SECONDS", 0.05)
    settings = get_settings()
    sync = OpenSearch(hosts=[settings.OPENSEARCH_URL])
    async_client = AsyncOpenSearch(hosts=[settings.OPENSEARCH_URL])
    repo = AlertRepository(
        async_client, settings.OPENSEARCH_INDEX, settings.OPENSEARCH_REQUEST_INDEX
    )

    async def never_disconnects() -> Message:
        await asyncio.Event().wait()
        return {"type": "http.disconnect"}

    request = Request({"type": "http"}, never_disconnects)
    stream = alerts_routes.stream_alerts(request, repo)
    extra = build_event(1, TEST_BASE)
    extra["event"]["id"] = "f" * 64
    index = "prebetter-test-events-2026.11.10"
    try:
        assert (await anext(stream)).comment == "connected"
        await asyncio.to_thread(
            sync.index,
            index=index,
            id=extra["event"]["id"],
            body=extra,
            params={"refresh": "true"},
        )
        event = await asyncio.wait_for(anext(stream), timeout=5)
        assert event.event == "alerts"
        assert event.data == {"count": 1}
    finally:
        await stream.aclose()
        sync.delete(index=index, id=extra["event"]["id"], params={"refresh": "true"})
        sync.close()
        await async_client.close()
