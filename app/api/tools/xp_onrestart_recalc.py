from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c
from app.api.exceptions import SnipsWeeklyXPResetError

from app.api.tools.xp_weekly_reset import reset_xp_current_week


def get_weekly_reset_cutover() -> datetime:
    now_utc = datetime.now(timezone.utc)
    last_monday = now_utc - timedelta(days=now_utc.weekday())
    closest_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)

    return closest_monday


def soft_reset_weekly_xp(db: Session):
    # set all weekly xp to 0 by default
    db \
        .query(models.User) \
        .update({
            models.User.xp_current_week: 0
        })
    
    # refresh virtual before committing
    db.flush()


def get_weekly_xp_per_user(db: Session, date_reset_cutover: datetime):
    return db \
        .query(
            models.XPTransaction.user_id,
            func.sum(models.XPTransaction.amount)
        ) \
        .filter(
            models.XPTransaction.date_credited >= date_reset_cutover
        ) \
        .group_by(
            models.XPTransaction.user_id
        ) \
        .all()


def set_user_weekly_xp(db: Session, user_id: int, new_xp_current_week: int):
    user = crud.get_user_by_id(db=db, id=user_id)
    user.xp_current_week = new_xp_current_week
    db.merge(user)


def recalc_xp(db: Session) -> bool:
    """
    For all users, set current week's XP to 0 
    """

    date_reset_cutover = get_weekly_reset_cutover()

    try:

        soft_reset_weekly_xp(db=db)
        weekly_xp_per_user = get_weekly_xp_per_user(db=db, date_reset_cutover=date_reset_cutover)

        for user_xp in weekly_xp_per_user:
            user_id, xp_current_week = user_xp
            set_user_weekly_xp(
                db=db,
                user_id=user_id,
                new_xp_current_week=xp_current_week
            )
            
        db.commit()

    except SQLAlchemyError as e:
        db.rollback()
        raise SnipsWeeklyXPResetError("Could not execute ad-hoc week XP reset")
            

if __name__ == "__main__":
    db = SessionLocal()
    # recalc_xp(db=db)

