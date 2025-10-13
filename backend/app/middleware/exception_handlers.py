from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request, exc):
        return await http_exception_handler(request, exc)
