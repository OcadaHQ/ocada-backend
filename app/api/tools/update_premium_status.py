import os
import logging
import json
import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
from app.api.tools.premium import validate_premium
import app.api.constants as c


def get_all_users(db: Session) -> list:
    """
    Find all users 
    """
    return db \
        .query(models.User) \
        .order_by(models.User.id.asc()) \
        .all()


if __name__ == "__main__":
    
    db = SessionLocal()
    REVCAT_PUBLIC_API_KEY = os.getenv("REVCAT_PUBLIC_API_KEY", "nokey")

    # Find eligible users and credit their portfolios
    users = get_all_users(db=db)
    for user in users:
        is_premium = validate_premium(
            user_id=user.id,
            secret_id=user.secret_id,
            revcat_public_api_key=REVCAT_PUBLIC_API_KEY,
            should_update_user=False
            )
        if user.is_premium != is_premium:
            user.is_premium = int(is_premium)
            print(user.id, is_premium)
            db.merge(user)
            db.commit()

