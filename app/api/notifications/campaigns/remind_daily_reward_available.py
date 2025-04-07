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


def remind_daily_reward_available():
    """
    Objective: increase daily engagement and retention within the first 30 days of user registration
    Campaign: send a daily reminder once the daily reward is available. Cron will validate this every 15-30 minutes

    For all players, select the ones who:
    - status=active
    - signed up within the last 30 days
    - have an uncollected daily reward in one of their portfolios (eligible for a daily reward)
    - have not received a reminder to collect the reward in the last 20 hours

    For each, complete the following actions:
    - Get all active push tokens
    - Send a push notification to each
    - Record the action in the campaign history    
    """
    db: Session = SessionLocal()


if __name__ == '__main__':
    pass