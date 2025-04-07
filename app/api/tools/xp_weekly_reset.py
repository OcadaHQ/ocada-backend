from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c
from app.api.exceptions import SnipsWeeklyXPResetError


def reset_xp_current_week(db: Session) -> bool:
    """
    For all users, set current week's XP to 0 
    """
    try:
        db \
            .query(models.User) \
            .update({
                models.User.xp_current_week: 0
            })

        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise SnipsWeeklyXPResetError("Could not execute regular weekly XP reset")
            

if __name__ == "__main__":
    db = SessionLocal()
    reset_xp_current_week(db=db)
