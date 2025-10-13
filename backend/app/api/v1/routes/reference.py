from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List
from app.database.config import get_prelude_db
from app.models.prelude import Classification, Impact, Analyzer
from app.api.v1.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/classifications", response_model=List[str])
async def get_unique_classifications(
    db: Session = Depends(get_prelude_db),
) -> List[str]:
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
        raise HTTPException(
            status_code=500, detail=f"Error fetching classifications: {str(e)}"
        )


@router.get("/severities", response_model=List[str])
async def get_unique_severities(
    db: Session = Depends(get_prelude_db),
) -> List[str]:
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
        raise HTTPException(
            status_code=500, detail=f"Error fetching severities: {str(e)}"
        )


@router.get("/analyzers", response_model=List[str])
async def get_unique_analyzers(
    db: Session = Depends(get_prelude_db),
) -> List[str]:
    """Get a list of unique analyzer names."""
    try:
        results = (
            db.execute(
                select(Analyzer.name)
                .where(
                    Analyzer.name.isnot(None),
                    Analyzer._parent_type == "A",
                    Analyzer._index == -1,
                )
                .distinct()
                .order_by(Analyzer.name)
            )
            .scalars()
            .all()
        )
        return list(results)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching analyzers: {str(e)}"
        )
