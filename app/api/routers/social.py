from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query, Path, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

import app.api.constants as c
from app.models import api_schema, enums
from app.api.dependencies import manager, SessionLocal, get_db
from app.api import crud

router = APIRouter()


@router.get("/leaderboard",
    response_model=List[api_schema.PortfolioUserView],
    tags=["social"])
def get_xp_leaderboard(
    q: Optional[str] = Query(
        None,
        title="Search query",
        description="Search for a portfolio by name",
        max_length=50),
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get leaderboard of users' portfolios sorted by users' XP
    """
    q_clean = q if q is None else q.strip()
    db_leaders = crud.get_xp_leaderboard(
        db=db, q=q_clean, timeframe='weekly',
        skip=skip, limit=limit)
    return db_leaders
