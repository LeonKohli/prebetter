import logging
import sys
import json
from datetime import datetime
import os
from typing import Any, Optional


class JsonFormatter(logging.Formatter):

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id  # type: ignore[attr-defined]

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logging(log_level: str = "INFO", environment: Optional[str] = None) -> None:
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_levels:
        print(f"Warning: Invalid log level '{log_level}'. Defaulting to 'INFO'.")
        log_level = "INFO"

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    if environment is None:
        environment = os.environ.get("ENVIRONMENT", "development").lower()
    else:
        environment = environment.lower()

    if environment == "production":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        print(f"Setting up JSON logging with level {log_level} in {environment} mode")
    else:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(log_format))
        print(
            f"Setting up development logging with level {log_level} in {environment} mode"
        )

    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    return logging.getLogger(name)
