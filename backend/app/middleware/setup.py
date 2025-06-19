"""Middleware setup for the application."""

from fastapi import FastAPI
from .cors import setup_cors_middleware
from .exception_handlers import setup_exception_handlers
from .request_tracking import request_middleware


def setup_middleware(app: FastAPI) -> None:
    """
    Set up all middleware for the application.

    This function configures:
    - CORS middleware
    - Request tracking middleware
    - Exception handlers

    Args:
        app: The FastAPI application instance
    """
    # Set up CORS middleware
    setup_cors_middleware(app)

    # Set up request tracking middleware
    app.middleware("http")(request_middleware)

    # Set up exception handlers
    setup_exception_handlers(app)
