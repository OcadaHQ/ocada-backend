import logging
import json
import datetime

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


def is_stale_account(user: models.User, days=c.STALE_ACCOUNT_DAYS) -> bool:
    """
    Check if the user account is stale.
    """
    if user.status == 'active':
        if user.date_last_active < (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=days)):
            return True
    return False



def has_portfolios(user: models.User) -> bool:
    """
    Check if the user has any portfolios.
    """
    if user.portfolios:
        return True
    return False

def has_null_experience(user: models.User) -> bool:
    """
    Check if the user has any portfolios.
    """
    if user.has_experience is None:
        return True
    return False

def delete_user(db, user_id: int):
    # exit()
    db_user = crud.get_user_by_id(db=db, id=user_id)
    if db_user is not None:
        try:
            db.delete(db_user)
            db.commit()
        except SQLAlchemyError as e:
            logging.error(e)
            db.rollback()
            

if __name__ == "__main__":
    
    db = SessionLocal()

    # delete_user(db=db, user_id=155)
    exit()


    # Find eligible users and credit their portfolios
    users = get_all_users(db=db)
    user_count = 0
    for user in users:

        # if is_stale_account(user=user, days=c.STALE_ACCOUNT_DAYS):
        #     print(f"Stale account: {user.id}")
        #     delete_user(db=db, user_id=user.id)
        #     user_count = user_count + 1
        #     continue
        if has_null_experience(user) and (not has_portfolios(user)) and is_stale_account(user=user, days=14):
            print(f"User has no portfolios: {user.id}")
            # delete_user(db=db, user_id=user.id)
            user_count = user_count + 1
            continue
        # elif  and is_stale_account(user=user, days=7):
        #     print(f"User has null experience: {user.id}")
        #     user_count = user_count + 1
        #     continue
            
    print(f"Found {user_count} stale accounts.")