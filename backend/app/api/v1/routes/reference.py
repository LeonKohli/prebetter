from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ....database.config import get_prelude_db
from ....models.prelude import Classification, Impact, Analyzer
from ..routes.auth import get_current_user
from sqlalchemy.sql import func

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/classifications", response_model=List[str])
async def get_unique_classifications(
    db: Session = Depends(get_prelude_db),
) -> List[str]:
    """Get a list of unique classification texts."""
    try:
        results = (
            db.query(Classification.text)
            .filter(Classification.text.isnot(None))
            .distinct()
            .order_by(Classification.text)
            .all()
        )
        return [result[0] for result in results]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching classifications: {str(e)}"
        )

@router.get("/severities", response_model=List[str])
async def get_unique_severities(
    db: Session = Depends(get_prelude_db),
) -> List[str]:
    """Get a list of unique impact severities."""
    try:
        results = (
            db.query(Impact.severity)
            .filter(Impact.severity.isnot(None))
            .distinct()
            .order_by(func.lower(Impact.severity))
            .all()
        )
        return [result[0] for result in results]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching severities: {str(e)}"
        )

@router.get("/analyzers", response_model=List[str])
async def get_unique_analyzers(
    db: Session = Depends(get_prelude_db),
) -> List[str]:
    """Get a list of unique analyzer names."""
    try:
        results = (
            db.query(Analyzer.name)
            .filter(
                Analyzer.name.isnot(None),
                Analyzer._parent_type == "A",
                Analyzer._index == -1,
            )
            .distinct()
            .order_by(Analyzer.name)
            .all()
        )
        return [result[0] for result in results]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching analyzers: {str(e)}"
        ) 