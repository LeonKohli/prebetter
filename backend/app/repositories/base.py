"""
Base repository class for common database operations.

Provides reusable patterns for:
- Session management
- Pagination helpers
- Common query operations
"""

from typing import TypeVar, Generic
from sqlalchemy.orm import Session
from sqlalchemy import Select, func, select

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository with common database operations.

    Usage:
        class AlertRepository(BaseRepository[Alert]):
            def __init__(self, db: Session):
                super().__init__(db)
    """

    def __init__(self, db: Session):
        self.db = db

    def count(self, query: Select) -> int:
        """
        Count total results for a query (for pagination).

        Uses subquery pattern for accurate counts with JOINs.
        """
        count_stmt = select(func.count()).select_from(query.distinct().subquery())
        return self.db.scalar(count_stmt) or 0

    def paginate(self, query: Select, offset: int, limit: int) -> list:
        """
        Apply pagination to query and execute.

        Args:
            query: SQLAlchemy select statement
            offset: Number of rows to skip
            limit: Maximum rows to return

        Returns:
            List of result rows
        """
        return self.db.execute(query.offset(offset).limit(limit)).all()

    def execute_one(self, query: Select):
        """Execute query and return first result or None."""
        return self.db.execute(query).first()

    def execute_all(self, query: Select) -> list:
        """Execute query and return all results."""
        return self.db.execute(query).all()

    def scalar(self, query: Select):
        """Execute query and return scalar value."""
        return self.db.scalar(query)
