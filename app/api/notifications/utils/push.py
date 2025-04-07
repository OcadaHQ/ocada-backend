import logging
import json
import datetime
import requests

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models, enums
import app.api.constants as c


def send_push(db: Session, user_id: int, token_provider: str, token_to: str, title: str, body: str, ttl: int, androidChannelId: str='default', badge_no: int=1, is_sound_played: bool=True):
    r = requests.post(
        url="https://exp.host/--/api/v2/push/send",
        headers={
            'content-type': 'application/json'
        },
        json={
            'to': token_to,
            'title': title,
            'body': body,
            'badge': badge_no,
            'channelId': androidChannelId,
            'sound': 'default' if is_sound_played else None,
            'priority': 'high',
        }
    )
    try:
        response = r.json()
        if response['data']['status'] != 'ok':
            return False
        
        receipt = models.PushReceipt(
            user_id=user_id,
            provider=token_provider,
            token=token_to,
            push_ticket_id=response['data']['id'],
            date_sent=func.now(),
            date_proxy_received=func.now(),
            date_accepted=None,
        )
        db.merge(receipt)
        db.commit()
    except Exception as e:
        db.rollback()
        print('push failed', e)
        return None
    

def get_all_push_tokens(db: Session) -> list:
    return db \
    .query(models.UserPushToken) \
    .filter(models.UserPushToken.status == 'active') \
    .all()


def get_push_tokens_by_weekly_bonus(db: Session) -> list:
    return db \
    .query(models.UserPushToken) \
    .join(models.Portfolio, models.Portfolio.user_id == models.UserPushToken.user_id) \
    .filter(
        or_(
            models.Portfolio.date_last_claimed_weekly_reward < (datetime.date.today() - datetime.timedelta(days=7)),
            models.Portfolio.date_last_claimed_weekly_reward == None,
            models.Portfolio.user_id == 2
        )
    ) \
    .filter(models.UserPushToken.status == 'active') \
    .order_by(models.UserPushToken.user_id.asc()) \
    .all()


def get_recent_push_tokens(db: Session, last_active_days_ago: int = 7) -> list:
    return db \
    .query(models.UserPushToken) \
    .join(models.User, models.User.id == models.UserPushToken.user_id) \
    .filter(models.UserPushToken.status == 'active') \
    .filter(models.User.date_last_active >= (datetime.date.today() - datetime.timedelta(days=5))) \
    .all()


def get_recent_push_receipts(db: Session) -> list:
    return db \
    .query(models.PushReceipt) \
    .filter(models.PushReceipt.date_sent >= datetime.date.today()) \
    .filter(models.PushReceipt.date_accepted == None) \
    .all()
