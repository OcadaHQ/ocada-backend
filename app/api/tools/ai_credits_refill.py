from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c
from app.api.exceptions import SnipsWeeklyXPResetError


def ai_credits_refill(db: Session) -> bool:
    """
    For all users, set current week's XP to 0 
    """
    try:
        db \
            .query(models.User) \
            .filter(
                models.User.credit_balance < 1000
            ) \
            .update({
                models.User.credit_balance: 1000
            })

        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception("Could not execute regular weekly XP reset")
            

if __name__ == "__main__":
    db = SessionLocal()
    ai_credits_refill(db=db)
