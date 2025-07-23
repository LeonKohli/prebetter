from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
import time
import uuid
import sqlalchemy.exc

logger = logging.getLogger(__name__)


async def request_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger_adapter = logging.LoggerAdapter(logger, {"request_id": request_id})
    logger_adapter.info(f"Request started: {request.method} {request.url.path}")
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        logger_adapter.info(
            f"Request completed: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Duration: {process_time:.3f}s"
        )

        return response

    except sqlalchemy.exc.OperationalError as e:
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
