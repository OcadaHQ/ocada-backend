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


def remind_weekly_reward_available():
    """
    Objective: keep weekly engagement and retention for registered users
    Campaign: send a daily reminder once the weekly reward is available. Cron will validate this every 60 minutes

    For all players, select the ones who:
    - status=active
    - have an uncollected weekly reward in one of their portfolios (=eligible for a weekly reward)
    - have not received a reminder to collect the weekly reward in the last 7 days

    For each, complete the following actions:
    - Get all active push tokens
    - Send a push notification to each
    - Record the action in the campaign history    
    """
    db: Session = SessionLocal()
    tokens = db \
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


if __name__ == '__main__':
    pass