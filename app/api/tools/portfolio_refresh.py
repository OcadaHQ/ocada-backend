import logging
import json
import datetime

from sqlalchemy.exc import IntegrityError
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


    # Find eligible users and credit their portfolios
    users = get_all_users(db=db)
    for user in users:
        for portfolio in user.portfolios:
            crud.refresh_portfolio_stats(db=db, portfolio_id=portfolio.id, refresh_timeout=0)
