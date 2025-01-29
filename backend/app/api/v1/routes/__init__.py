from .alerts import router as alerts_router
from .statistics import router as statistics_router
from .reference import router as reference_router

__all__ = ["alerts_router", "statistics_router", "reference_router"]
