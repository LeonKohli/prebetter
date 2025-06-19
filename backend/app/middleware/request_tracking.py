"""Request tracking middleware for adding request IDs and logging."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
import time
import uuid
import sqlalchemy.exc

# Get logger
logger = logging.getLogger(__name__)


async def request_middleware(request: Request, call_next):
    """
    Middleware for tracking requests with unique IDs and logging.

    This middleware:
    - Generates a unique request ID for each request
    - Adds the request ID to the request state
    - Logs request start and completion
    - Adds the request ID to response headers
    - Handles database and general exceptions

    Args:
        request: The incoming request
        call_next: The next middleware or route handler

    Returns:
        The response from the next middleware or route handler
    """
    # Generate a unique request ID
    request_id = str(uuid.uuid4())

    # Add request ID to request state
    request.state.request_id = request_id

    # Add request ID to all log records in this context
    logger_adapter = logging.LoggerAdapter(logger, {"request_id": request_id})

    # Log request start with path and method
    logger_adapter.info(f"Request started: {request.method} {request.url.path}")
    start_time = time.time()

    try:
        # Process the request
        response = await call_next(request)

        # Calculate request duration
        process_time = time.time() - start_time

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log request completion
        logger_adapter.info(
            f"Request completed: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Duration: {process_time:.3f}s"
        )

        return response

    except sqlalchemy.exc.OperationalError as e:
        # Database connection errors
        process_time = time.time() - start_time
        logger_adapter.error(
            f"Database connection error: {str(e)} - "
            f"Request: {request.method} {request.url.path} - Duration: {process_time:.3f}s"
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Database connection error. Please try again later.",
                "request_id": request_id,
            },
        )
    except sqlalchemy.exc.SQLAlchemyError as e:
        # General SQLAlchemy errors
        process_time = time.time() - start_time
        logger_adapter.error(
            f"Database error: {str(e)} - "
            f"Request: {request.method} {request.url.path} - Duration: {process_time:.3f}s"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred.", "request_id": request_id},
        )
    except Exception as e:
        # Catch all other exceptions
        process_time = time.time() - start_time
        logger_adapter.error(
            f"Unhandled exception: {str(e)} - "
            f"Request: {request.method} {request.url.path} - Duration: {process_time:.3f}s",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected error occurred.",
                "request_id": request_id,
            },
        )
