from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query, Path, Body
from sqlalchemy.orm import Session

import app.api.constants as c
from app.models import api_schema
from app.api.dependencies import manager, SessionLocal, get_db
from app.api import crud

router = APIRouter()


# todo: create crud

@router.get("/event_types", response_model=List[api_schema.EventType], tags=["events"])
def get_events(
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    db = SessionLocal()
    event_types = crud.get_event_types(db=db, skip=skip, limit=limit)
    return event_types


@router.get("/events", response_model=List[api_schema.Event], tags=["events"])
def get_events(
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    db = SessionLocal()
    events = crud.get_events(db=db, user_id=user.id, skip=skip, limit=limit)
    return events


@router.post("/events", response_model=List[api_schema.Event], tags=["events"])
def trigger_event(
    db: Session = Depends(get_db),
    event_type_id: int = Query(
        gt=0
    ),
    user=Depends(manager)
):
    db = SessionLocal()
    event = crud.trigger_event(
        db=db, user_id=user.id, event_type_id=event_type_id)
    return event


@router.get("/events/{event_id}", response_model=api_schema.Event, tags=["events"])
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    db = SessionLocal()
    event = crud.get_event_by_id(db=db, event_id=event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
