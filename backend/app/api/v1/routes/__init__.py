from .alerts import router as alerts_router
from .statistics import router as statistics_router
from .reference import router as reference_router
from .auth import router as auth_router
from .users import router as users_router

__all__ = ["alerts_router", "statistics_router", "reference_router", "auth_router", "users_router"]
