import logging
import sys
import json
from datetime import datetime, timezone
import os


class JsonFormatter(logging.Formatter):
    """JSON formatter for production logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, default=str)


def setup_logging(log_level: str = "INFO", environment: str | None = None) -> None:
    """Configure application logging.

    Args:
        log_level: DEBUG, INFO, WARNING, ERROR, or CRITICAL
        environment: 'production' for JSON output, anything else for human-readable
    """
    if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        log_level = "INFO"

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level))

    # Clear existing handlers
    for h in root.handlers[:]:
        root.removeHandler(h)

    env = (environment or os.environ.get("ENVIRONMENT", "development")).lower()

    handler = logging.StreamHandler(sys.stdout)
    if env == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    root.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
