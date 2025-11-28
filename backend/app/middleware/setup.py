from fastapi import FastAPI
from .cors import setup_cors_middleware
from .request_tracking import request_middleware


def setup_middleware(app: FastAPI) -> None:
    setup_cors_middleware(app)
    app.middleware("http")(request_middleware)
