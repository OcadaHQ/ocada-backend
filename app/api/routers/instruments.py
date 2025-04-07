from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query, Path, Body
from sqlalchemy.orm import Session

import app.api.constants as c
from app.models import api_schema
from app.api.dependencies import manager, SessionLocal, get_db
from app.api import crud

router = APIRouter()


@router.get("/instruments", response_model=List[api_schema.Instrument], tags=["instruments"])
def get_instruments(
    q: Optional[str] = Query(
        None,
        title="Search query",
        description="Search for an instrument by name",
        # min_length=3,
        max_length=50),
    shuffle: Optional[bool] = Query(
        False,
        title="Shuffle instruments",
        description="Shuffle the instruments",
    ),
    show_well_known_only: Optional[bool] = Query(
        None,
        title="Show well known instruments only",
        description="Show well known instruments only",
    ),
    collection_id: Optional[int] = Query(
        None,
        title="The unique ID of a collection",
        ge=1
    ),
    sort: Optional[str] = Query(
        None,
        title="Sort instruments",
        description="Sort the instruments",
        enum=["name_asc", "shuffle", "price_change_perc_asc", "price_change_perc_desc"]
    ),
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    # user=Depends(manager)
):
    """
    Get all instruments
    """
    q_clean = q if q is None else q.strip()
    sort = 'shuffle' if shuffle else sort

    if collection_id is None:
        db_instruments = crud.get_instruments(
            db=db, q=q_clean, sort=sort, show_well_known_only=show_well_known_only, skip=skip, limit=limit)
    else:
        db_instruments = crud.get_instruments_by_collection_id(db=db, q=q_clean, collection_id=collection_id, skip=skip, limit=limit)
    return db_instruments


# async/sync: https://fastapi.tiangolo.com/async/#in-a-hurry
@router.get("/instruments/{instrument_id}", response_model=api_schema.Instrument, tags=["instruments"])
def get_instrument(
    instrument_id: int = Path(...,
                              title="The instrument unique identifier", ge=1),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get instrument by ID
    """
    db_instrument = crud.get_instrument_by_id(db=db, id=instrument_id)
    if db_instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return db_instrument


@router.get("/instruments/{instrument_id}/bars", response_model=List[api_schema.InstrumentPriceHistoryBar], tags=["instruments"])
def get_instrument_bars(
    instrument_id: int = Path(...,
                              title="The instrument unique identifier", ge=1),
    lookback_days: Optional[int] = Query(
        None,
        ge=1,
        title="(deprecated) How many days to look back",
        description="(deprecated) How many days to look back",
    ),
    lookback_hours: Optional[int] = Query(
        24,
        ge=1,
        title="How many hours to look back",
        description="How many hours to look back",
    ),
    bar_interval: Optional[str] = Query(
        '1D',
        title="Bar interval",
        description="1m = 1 minute, 1H = 1 hour, 1D = 1 day",
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get instrument bars (price history) by instrument ID
    """
    db_instrument = crud.get_instrument_by_id(db=db, id=instrument_id)
    if db_instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    if lookback_days:
        lookback_hours = lookback_days * 24
    db_bars = crud.get_instrument_bars(
        db=db, instrument_id=instrument_id,
        lookback_hours=lookback_hours, bar_interval=bar_interval)
    return db_bars


@router.get("/collections", response_model=List[api_schema.InstrumentCollection], tags=["instruments"])
def get_collections(
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get all collections
    """
    db_collections = crud.get_collections(db=db, skip=skip, limit=limit)
    return db_collections

