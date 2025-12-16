"""
Repository layer for data access.

Following FastAPI best practices - repositories encapsulate all database queries
and return domain objects. Routes/services never touch SQLAlchemy directly.
"""

from .alerts import AlertRepository

__all__ = ["AlertRepository"]
