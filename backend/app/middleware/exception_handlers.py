"""Exception handlers for the application."""

from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException

def setup_exception_handlers(app: FastAPI) -> None:
    """
    Configure exception handlers for the application.
    
    Args:
        app: The FastAPI application instance
    """
    
    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request, exc):
        """
        Custom handler for HTTP exceptions.
        
        Args:
            request: The request that caused the exception
            exc: The exception that was raised
            
        Returns:
            The response from the default HTTP exception handler
        """
        return await http_exception_handler(request, exc) 