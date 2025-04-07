from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query, Path, Body
from sqlalchemy.orm import Session

import app.api.constants as c
from app.models import api_schema
from app.api.dependencies import manager, SessionLocal, get_db
from app.api import crud

router = APIRouter()


@router.get("/characters", response_model=List[api_schema.Character], tags=["characters"])
def get_characters(
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    db = SessionLocal()
    characters = crud.get_characters(db=db, skip=skip, limit=limit)
    return characters


@router.get("/characters/{character_id}", response_model=api_schema.Character, tags=["characters"])
def get_character(
    character_id: int,
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    db = SessionLocal()
    character = crud.get_character_by_id(db=db, id=character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return character
