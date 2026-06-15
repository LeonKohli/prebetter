import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.config import get_prelude_db
from app.models.prelude import Classification, Impact, Node

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user, scope="function")])


@router.get("/classifications", response_model=list[str])
def get_unique_classifications(
    db: Annotated[Session, Depends(get_prelude_db)],
) -> list[str]:
    """Get a list of unique classification texts."""
    try:
        results = (
            db.execute(
                select(Classification.text)
                .where(Classification.text.isnot(None))
                .distinct()
                .order_by(Classification.text)
            )
            .scalars()
            .all()
        )
        return list(results)
    except Exception as e:
        logger.exception("Error fetching classifications: %s", e)
        raise HTTPException(status_code=500, detail="Error fetching classifications")


@router.get("/severities", response_model=list[str])
def get_unique_severities(
    db: Annotated[Session, Depends(get_prelude_db)],
) -> list[str]:
    """Get a list of unique impact severities."""
    try:
        results = (
            db.execute(
                select(Impact.severity)
                .where(Impact.severity.isnot(None))
                .distinct()
                .order_by(func.lower(Impact.severity))
            )
            .scalars()
            .all()
        )
        return list(results)
    except Exception as e:
        logger.exception("Error fetching severities: %s", e)
        raise HTTPException(status_code=500, detail="Error fetching severities")


@router.get("/servers", response_model=list[str])
def get_unique_servers(
    db: Annotated[Session, Depends(get_prelude_db)],
) -> list[str]:
    """Get a list of unique short node names (servers like server-001)."""
    try:
        # Analyzer-node rows (_parent_type='A', _parent0_index=-1) map 1:1 to the
        # index=-1 analyzers, so we read node names directly instead of joining
        # back through Analyzer (verified equivalent on prod; drops a 786k-row
        # join). Still ~104k rows -> 7 names, hence DISTINCT.
        results = (
            db.execute(
                select(Node.name)
                .where(
                    Node._parent_type == "A",
                    Node._parent0_index == -1,
                    Node.name.isnot(None),
                )
                .distinct()
            )
            .scalars()
            .all()
        )

        # Extract short node name (before first dot)
        short_nodes = {name.split(".")[0] for name in results if name}
        return sorted(short_nodes)
    except Exception as e:
        logger.exception("Error fetching servers: %s", e)
        raise HTTPException(status_code=500, detail="Error fetching servers")
