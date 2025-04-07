import logging
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c


def get_users_with_email(db: Session) -> list:
    """
    Find all users 
    """
    return db \
        .query(models.User) \
        .filter(
            models.User.email != None
        ) \
        .filter(
            models.User.email_opt_out == 0
        ) \
        .order_by(models.User.date_last_active.desc()) \
        .all()


def is_active(user: models.User, delta_lapsed: timedelta):
    now = datetime.now(tz=timezone.utc)
    return (now - delta_lapsed) < user.date_last_active

if __name__ == "__main__":

    db = SessionLocal()
    delta_lapsed = timedelta(days=30)

    users = get_users_with_email(db=db)
    n_active = 0
    n_lapsed = 0


    # with open("users_active.csv", "w") as f_active:
    #     with open("user_lapsed.csv", "w") as f_lapsed:
    #         f_active.write("email,snips_user_id\n")
    #         f_lapsed.write("email,snips_user_id\n")

    #         for user in users:
    #             if is_active(user=user, delta_lapsed=delta_lapsed):
    #                 n_active += 1
    #                 f_active.write(f"{user.email},{user.id}\n")
    #             else:
    #                 n_lapsed += 1
    #                 f_lapsed.write(f"{user.email},{user.id}\n")

    #         print(f"# of MAU: {n_active}")
    #         print(f"# of lapsed: {n_lapsed}")

    with open("newsletter_subs_2023_05_27.csv", "w") as f_users:
        f_users.write("email,snips_user_id\n")

        for user in users:
            f_users.write(f"{user.email},{user.id}\n")
    
