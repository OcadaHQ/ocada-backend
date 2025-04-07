import logging
import json
import datetime
import requests

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models, enums
import app.api.constants as c


def get_recent_push_receipts(db: Session) -> list:
    return db \
    .query(models.PushReceipt) \
    .filter(models.PushReceipt.date_sent >= datetime.date.today()) \
    .filter(models.PushReceipt.date_accepted == None) \
    .all()


def is_push_accepted(db: Session, receipt: models.PushReceipt):
    ticket_id = receipt.push_ticket_id
    r = requests.post(
        url="https://exp.host/--/api/v2/push/getReceipts",
        headers={
            'content-type': 'application/json'
        },
        json={
            'ids': [
                ticket_id
            ]
        }
    )

    try:
        response = r.json()['data']
        print(response)
        if response[ticket_id]['status'] == 'ok':
            return True
        elif response[ticket_id]['status'] == 'error':
            return response[ticket_id]['details']['error']
        
    except Exception as e:
        print('failed to validate the receipt', e)
        return None



def validate_receipts(db: Session):
    receipts = get_recent_push_receipts(db=db)
    for receipt in receipts:
        status = is_push_accepted(db=db, receipt=receipt)
        try:
            if status is True:
                crud.activate_push_token(db=db, provider=receipt.provider, token=receipt.token, user_id=receipt.user_id)
                receipt.date_accepted = func.now()
                db.merge(receipt)
                db.commit()
            elif status is not None:
                crud.disable_push_token(db=db, provider=receipt.provider, token=receipt.token)
        except Exception as e:
            db.rollback()
            print('error validating push accept ', e)


if __name__ == "__main__":
    
    db = SessionLocal()

    validate_receipts(db=db)

