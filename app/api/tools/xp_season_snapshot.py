from datetime import datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c
from app.api.exceptions import SnipsWeeklyXPResetError


def take_xp_snapshot(db: Session):
    """
    todo: 
    - update timeframe_label
    - update timeframe
    - set up cron
    """
    timeframe_label = '1W'  
    date_as_of = datetime.now().strftime('%Y-%m-%d 00:00:00+00')
    results = crud.get_xp_leaderboard(db=db, q=None, skip=0, limit=100, timeframe='season')
    for portfolio in results:
        xp_score = portfolio.user.xp_current_week
        if xp_score == 0:
            break
        user_xp_snapshot = models.XPSnapshot(
            user_id=portfolio.user.id,
            timeframe=timeframe_label,
            date_as_of=date_as_of,
            xp_collected=xp_score,
        )
        db.merge(user_xp_snapshot)
    try:
        db.commit()
    except:
        db.rollack()


def reset_xp_current_season(db: Session) -> bool:
    """
    For all users, set current week's XP to 0 
    """
    try:
        db \
            .query(models.User) \
            .update({
                models.User.xp_current_season: 0
            })

        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise SnipsWeeklyXPResetError("Could not execute regular seasonly XP reset")
            

if __name__ == "__main__":
    db = SessionLocal()
    take_xp_snapshot(db=db)
    reset_xp_current_season(db=db)
