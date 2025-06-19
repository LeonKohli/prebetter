"""CORS middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..core.config import get_settings


def setup_cors_middleware(app: FastAPI) -> None:
    """
    Configure CORS middleware for the application.

    Args:
        app: The FastAPI application instance
    """
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
