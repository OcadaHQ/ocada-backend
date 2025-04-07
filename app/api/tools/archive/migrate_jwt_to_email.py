"""
This was used to migrate email addresses from JWT tokens to the users table
"""

import logging
import json
import datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c

from app.api.auth.apple_auth import AppleAuth
from app.api.auth.google_auth import GoogleAuth


def get_all_users(db: Session) -> list:
    """
    Find all users 
    """
    return db.query(models.User).all()


if __name__ == "__main__":
    exit()
    db = SessionLocal()
    apple_auth = AppleAuth()
    google_auth = GoogleAuth()

    # this code should not be run again
    users = get_all_users(db=db)
    for user in users:
        for account in user.accounts:
            detail_raw = account.detail


            try:
                detail = json.loads(detail_raw)
            except Exception as e:
                # print("Exception: ", user.id, account.detail)
                if account.provider == 'apple':
                    ext_user = apple_auth.validate_jwt(apple_user_token=detail_raw)
                    detail = ext_user.raw
                    account.detail = json.dumps(ext_user.raw)
                    db.merge(account)
                    db.commit()
                elif account.provider == 'google':
                    detail = None
                    account.detail = None
                    db.merge(account)
                    db.commit()
                    continue
                    # ext_user = google_auth.validate_access_token(access_token=detail_raw)

        
            user.email = detail.get('email', None)
            db.merge(user)
            db.commit()
            print(account.provider, user.id, detail['email'])
            
            break
