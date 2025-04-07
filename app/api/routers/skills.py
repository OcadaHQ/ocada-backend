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


@router.get("/skills", tags=["skill"])
def get_skills(
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    target_user_id: Optional[int] = Query(
        None,
        title="The user ID to query skills for",
        ge=1,
    )
):
    return []


@router.post("/skills/{skill_key}/discover", tags=["skill"])
def discover_skill(
    skill_key: str = Path(...,
        title="The unique key associated with the skill"
    )
):
    raise HTTPException(status_code=404, detail="Skill not found")


@router.get("/skills/{skill_key}/quiz", tags=["skill"])
def get_quiz_details(
    skill_key: str = Path(...,
        title="The unique key associated with the skill"
    ),
):
    raise HTTPException(status_code=404, detail="Skill not found or you have not discovered it yet")


@router.post("/skills/{skill_key}/quiz", tags=["skill"])
def submit_quiz(
    skill_key: str = Path(...,
        title="The unique key associated with the skill"
    ),
    submitted_answers: api_schema.QuizSubmissionInput = Body(
        ...,
        title="Answers supplied by the user",
        embed=True
    ),
):
    raise HTTPException(status_code=404, detail="Skill not found or you have not discovered it yet")


@router.post("/skills/{skill_key}/quiz_answer_attempt", tags=["skill"])
def log_quiz_answer_attempt(
    skill_key: str = Path(...,
        title="The unique key associated with the skill"
    ),
    question_id: int = Body(
        ...,
        title="Question ID"
    ),
    answer_id: int = Body(
        ...,
        title="Answer ID"
    ),
):
    return {
        "detail": "Attempt has been saved"
    }


@router.get("/skills/list", tags=["skill"])
def get_user_skills_list():
    return {
        'discovered': [],
        'unlocked': []
    }