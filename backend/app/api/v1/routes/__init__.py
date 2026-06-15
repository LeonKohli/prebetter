from .alerts import router as alerts_router
from .statistics import router as statistics_router
from .reference import router as reference_router
from .export import router as export_router
from .heartbeats import router as heartbeats_router

__all__ = [
    "alerts_router",
    "statistics_router",
    "reference_router",
    "export_router",
    "heartbeats_router",
]
