from fastapi import APIRouter, Depends

from app.api.deps import Alerts, get_current_user
from app.schemas.filters import SEVERITY_LABELS

router = APIRouter(dependencies=[Depends(get_current_user, scope="function")])


@router.get("/severities")
async def get_severities() -> list[str]:
    return list(SEVERITY_LABELS)


@router.get("/servers")
async def get_servers(repo: Alerts) -> list[str]:
    """Sorted sensor names."""
    return await repo.sensors()


@router.get("/classifications")
async def get_classifications(repo: Alerts) -> list[str]:
    """Sorted rule names."""
    return await repo.rule_names()
