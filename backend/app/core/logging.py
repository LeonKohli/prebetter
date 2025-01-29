import logging
import logging.handlers
import sys
import os
from datetime import datetime
from typing import Any
from pathlib import Path


def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration with file and console handlers"""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create formatters
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(pathname)s:%(lineno)d]"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # File handlers
    # Main log file with rotation
    main_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    main_handler.setFormatter(file_formatter)
    main_handler.setLevel(logging.INFO)

    # Error log file with rotation
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setFormatter(file_formatter)
    error_handler.setLevel(logging.ERROR)

    # Access log file with rotation
    access_handler = logging.handlers.RotatingFileHandler(
        log_dir / "access.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    access_handler.setFormatter(file_formatter)
    access_handler.setLevel(logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(main_handler)
    root_logger.addHandler(error_handler)

    # Configure access logger
    access_logger = logging.getLogger("access")
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(access_handler)


def get_logger(name: str) -> Any:
    """Get logger instance with the specified name"""
    return logging.getLogger(name)


def log_request(request, response_status: int, duration: float) -> None:
    """Log API request details"""
    logger = get_logger("access")
    logger.info(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "status_code": response_status,
            "duration_ms": round(duration * 1000, 2),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
    ) 