import logging
import sys
from typing import Any


def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration"""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, log_level),
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> Any:
    """Get logger instance"""
    return logging.getLogger(name) 