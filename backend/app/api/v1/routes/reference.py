import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.config import get_node_join_conditions, get_prelude_db
from app.models.prelude import Analyzer, Classification, Impact, Node

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
        results = (
            db.execute(
                select(Node.name)
                .select_from(Analyzer)
                .outerjoin(
                    Node,
                    get_node_join_conditions(
                        Analyzer._message_ident, "A", Analyzer._index
                    ),
                )
                .where(
                    Analyzer.name.isnot(None),
                    Analyzer._parent_type == "A",
                    Analyzer._index == -1,
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
