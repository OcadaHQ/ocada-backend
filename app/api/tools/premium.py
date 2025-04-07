import requests
from pprint import pprint
from dateutil import parser
from datetime import datetime

from app.api.database import engine, SessionLocal
from app.models import models
from app.api import crud
import app.api.constants as c


def validate_premium(user_id, secret_id, revcat_public_api_key, should_update_user=False):
    is_user_premium = False
    revcat_user_id = f"{user_id}_{secret_id}"
    url = f"https://api.revenuecat.com/v1/subscribers/{revcat_user_id}"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {revcat_public_api_key}"
    }

    response = requests.get(url, headers=headers)

    try:
        premium_data = response.json()['subscriber']['entitlements']['Premium']
    except(Exception) as e:
        pass
    
    try:
        if premium_data['expires_date'] is None:
            is_user_premium = True
        else:
            expires_date = parser.isoparse(premium_data['expires_date'])
            grace_period_expires_date = parser.isoparse(premium_data['grace_period_expires_date']) if premium_data['grace_period_expires_date'] is not None else expires_date
            now = datetime.now(expires_date.tzinfo)
    
            if expires_date >= now or grace_period_expires_date >= now:
                is_user_premium = True

    except(Exception) as e:
        pass

    if should_update_user:
        db = SessionLocal()
        user = crud.get_user_by_id(db=db, id=user_id)
        was_user_premium = bool(user.is_premium)
        # if the user upgrades from free to premium
        print(was_user_premium, is_user_premium)
        if not was_user_premium and is_user_premium:
            crud.add_credits_by_user_id(db=db, user_id=user_id, credit_amount=c.AI_CREDIT.PREMIUM_USER_ADD)
        user.is_premium = int(is_user_premium)
        db.merge(user)
        db.commit()

    return is_user_premium


# if __name__ == "__main__":


#     is_premium = validate_premium(
#         # user_id=2,
#         # secret_id='aae3bc470bce4726896029861f3f3ac8',
#         user_id=16,
#         secret_id='8bcb4a2629e245208072002f3a385a70',
#         revcat_public_api_key='appl_VXwXORmwULLPRBuyFOygSIWaWiq',
#         should_update_user=True,
#     )

#     print('is premium?', is_premium)
