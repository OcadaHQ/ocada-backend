from typing import List, Optional
import random

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query, Path, Body
from sqlalchemy import func, and_
from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import SQLAlchemyError

import app.api.constants as c
from app.models import api_schema, models
from app.api.dependencies import manager, SessionLocal, get_db
from app.api import crud

router = APIRouter()


@router.get(
    "/learn/user_skills", 
    response_model=List[api_schema.SkillStatView],
    tags=["learn"]
)
def get_user_skills(
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    result = db.query(
        models.Skill.id.label('id'),
        models.Skill.name.label('name'),
        models.Skill.description.label('description'),
        func.count(models.LessonSkill.lesson_id).label('n_lesson_total'),
        func.count(models.UserLesson.lesson_id).label('n_lessons_completed'),
    ).join(
        models.LessonSkill
    ).join(
        models.Lesson
    ).join(
        models.UserLesson,
        and_(models.Lesson.id == models.UserLesson.lesson_id, models.UserLesson.user_id == user.id),
        isouter=True
    ).group_by(
        models.Skill.id, models.Skill.name, models.Skill.description
    ).order_by(
        models.Skill.id
    ).all()

    return result


@router.get(
    "/learn/lesson/next",
    response_model=Optional[api_schema.LessonView],
    tags=["learn"]
)
def get_next_uncompleted_lesson(
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    # Create aliases for the tables to avoid ambiguity in the JOIN
    l = aliased(models.Lesson)
    ul = aliased(models.UserLesson)

    # Perform the LEFT OUTER JOIN and filter by user_id and uncompleted lessons
    query = db \
        .query(l) \
        .outerjoin(
            ul, (l.id == ul.lesson_id) & (ul.user_id == user.id)
        ) \
        .filter(
            (ul.user_id == None) | (ul.date_last_completed == None)
        )
    
    # Order by priority and select the first row
    next_lesson = query.order_by(l.priority).first()

    # shuffle the answers if applicable
    if next_lesson and next_lesson.quiz_questions:
        for index, _ in enumerate(next_lesson.quiz_questions):
            if next_lesson.quiz_questions[index].quiz_answers:
                random.shuffle(next_lesson.quiz_questions[index].quiz_answers)

    # 'next_lesson' will be None if all lessons have been completed
    return next_lesson



@router.post(
    "/learn/lesson/{lesson_id}/quiz",
    response_model=api_schema.LessonSubmissionResult,
    tags=["learn"]
)
def submit_lesson(
    lesson_id: int = Path(...,
        title="Lesson ID the user is submitting"
    ),
    submitted_answers: api_schema.LessonSubmissionInput = Body(
        ...,
        title="Answers supplied by the user",
        embed=True
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    db_lesson = crud.get_lesson_by_id(db=db, lesson_id=lesson_id)
    db_user_lesson = crud.get_user_lesson_by_id(db=db, lesson_id=lesson_id, user_id=user.id)
    if db_lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    is_first_attempt = db_user_lesson is None
    quiz_result_summary = {
        "passed": False,
        "passed_before": not is_first_attempt,
        "n_questions": len(db_lesson.quiz_questions),
        "n_correct_answers": 0
    }
    xp_credited = 0
    
    # loop through all questions to complete the lesson
    for question in db_lesson.quiz_questions:
        # loop through all possible answers to the question
        for answer in question.quiz_answers:
            # find the correct answer
            if answer.is_correct:
                # check if the submitted answer matches the correct answer
                if answer.id == submitted_answers.__root__.get(question.id, -1):
                    quiz_result_summary["n_correct_answers"] = quiz_result_summary["n_correct_answers"] + 1
                    break

    if quiz_result_summary["n_questions"] == quiz_result_summary["n_correct_answers"]:
        quiz_result_summary["passed"] = True
        db_user_lesson = crud.mark_lesson_as_completed(db=db, lesson_id=lesson_id, user_id=user.id)

        # credit XP for completing a quiz for the first time
        if is_first_attempt:
            try:
                xp_credited = c.XP_CREDIT.COMPLETE_LESSON_FIRST_TIME
                crud.credit_xp_by_user_id(
                    db=db,
                    user_id=user.id,
                    xp_amount=c.XP_CREDIT.COMPLETE_LESSON_FIRST_TIME,
                    xp_reason=c.XP_REASON.COMPLETE_LESSON_FIRST_TIME,
                    xp_detail=f"LESSON={lesson_id}"
                )
            except Exception as e:
                db.rollback()

    return {
        "lesson_id": lesson_id,
        "summary": quiz_result_summary,
        "xp_credited": xp_credited
    }
