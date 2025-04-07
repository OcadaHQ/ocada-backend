import os
import json

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

import app.api.constants as c
from app.models import models
from app.api.dependencies import manager, SessionLocal, get_db
from app.api import crud


def import_lesson_group(lesson_group):
    db = SessionLocal()
    for lesson_raw in lesson_group['data']:
        lesson = models.Lesson(
            name = lesson_raw['name'],
            lesson_text = lesson_raw['text']
        )
        db.add(lesson)
        db.flush()

        for question_raw in lesson_raw['questions']:
            question = models.QuizQuestion(
                lesson_id = lesson.id,
                question_text = question_raw['text']
            )
            db.add(question)
            db.flush()

            for answer_raw in question_raw['answers']:
                answer = models.QuizAnswer(
                    question_id = question.id,
                    answer_text = answer_raw['text'],
                    is_correct = (1 if answer_raw['is_correct'] else 0)
                )
                db.add(answer)
                db.flush()

    db.commit()


if __name__ == '__main__':

    raw_json_dir = 'app/api/tools/lessons/raw/'
    raw_json_files = os.listdir(raw_json_dir)

    for raw_json_file_name in raw_json_files:
        with open(raw_json_dir + raw_json_file_name) as f:
            lesson_group = json.load(f)
            import_lesson_group(lesson_group)