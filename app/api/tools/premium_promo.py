import os
import requests
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session


from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c

def get_users(db: Session) -> list:
    """
    Find all users 
    """
    return db \
        .query(models.User) \
        .filter(models.User.status == 'active') \
        .order_by(models.User.id.asc()) \
        .all()


def grant_promo_entitlement(
        user_id: int, secret_id: str,
        revcat_secret_key: str,
        entitlement_id: str = 'Premium', entitlement_duration: str = 'three_day',
    ):

    url = f"https://api.revenuecat.com/v1/subscribers/{user_id}_{secret_id}/entitlements/{entitlement_id}/promotional"

    payload = {"duration": entitlement_duration}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {revcat_secret_key}"
    }

    response = requests.post(url, json=payload, headers=headers)

    print(response.text)

if __name__ == '__main__':
    REVCAT_PRIVATE_API_KEY = os.getenv('REVCAT_PRIVATE_API_KEY')
    entitlement_id = 'Premium'
    duration = 'three_day'

    db = SessionLocal()
    users = get_users(db=db)

    for user in users:

        # group A: users with even user ID
        # if user.id % 2 == 0:
        # group B: users with odd user ID
        if user.id % 2 != 0:
            grant_promo_entitlement(
                user_id=user.id,
                secret_id=user.secret_id,
                revcat_secret_key=REVCAT_PRIVATE_API_KEY,
                entitlement_id='Premium',
                entitlement_duration='three_day'
            )
