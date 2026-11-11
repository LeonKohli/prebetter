from opensearchpy import AsyncOpenSearch

from app.core.config import Settings


def create_client(settings: Settings) -> AsyncOpenSearch:
    """Build the client for the app lifetime; an https URL enables TLS with certificate verification."""
    auth = (
        (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD or "")
        if settings.OPENSEARCH_USER
        else None
    )
    return AsyncOpenSearch(hosts=[settings.OPENSEARCH_URL], http_auth=auth)
