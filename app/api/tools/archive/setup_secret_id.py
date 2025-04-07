"""
This was used to enable secret_id for existing users
secret_id is a random string used to protect user purchases in revenuecat
revenue cat user id is constructed using both the regular user ID and secret ID
"""

import logging
import json
import datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c


def get_all_users(db: Session) -> list:
    """
    Find all users 
    """
    return db.query(models.User).all()


if __name__ == "__main__":
    
    db = SessionLocal()
    exit()

    # this code should not be run again
    # users = get_all_users(db=db)
    # for user in users:
    #     print(user.secret_id)
    #     user.secret_id = secret_id=uuid4().hex
    #     db.merge(user)
    #     db.commit()




