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
from app.api.notifications.utils.push import send_push


def get_user_tokens_with_old_holdings(db: Session):
    return db \
    .query(models.UserPushToken) \
    .join(models.Portfolio, models.Portfolio.user_id == models.UserPushToken.user_id) \
    .join(models.Holding, models.Portfolio.id == models.Holding.portfolio_id) \
    .filter(
        models.Holding.date_last_updated < (datetime.date.today() - datetime.timedelta(days=30)),
        models.Holding.quantity > 0,
    ) \
    .filter(
        models.UserPushToken.status == 'active',
        models.Portfolio.status == 'active',
        models.User.status == 'active'
    ) \
    .order_by(models.UserPushToken.user_id.asc()) \
    .all()

def get_relevant_old_holding_by_user_id(db: Session, user_id: int):
    return db \
    .query(models.Holding) \
    .join(models.Portfolio, models.Portfolio.id == models.Holding.portfolio_id) \
    .filter(
        models.Portfolio.user_id == user_id,
        models.Holding.date_last_updated < (datetime.date.today() - datetime.timedelta(days=30)),
        models.Holding.quantity > 0,
    ) \
    .group_by(
        models.Holding.portfolio_id, models.Holding.instrument_id
    ) \
    .order_by(
        func.max(models.Holding.quantity * models.Holding.average_price).desc()
    ) \
    .first()


def remind_invest_again():
    """
    Objective: increase engagement for T+30 users
    Campaign: send a reminder (once every 3 days max) once we identify the user has not invested in a stock for more than 30 days. Cron will validate this every 6 hours

    For all players, select the ones who:
    - status=active
    - have holdings matching:
        - quantity > 0
        - date_last_updated < 30 days ago
        - instrument is not retired

    For each matching player:
    - Get all active push tokens
    - Send a push notification to each
    - Reference the matching instrument
    - Record the action in the campaign history    
    """
    campaign_key = 'REMIND_INVEST_AGAIN'
    db: Session = SessionLocal()

    matching_user_tokens = get_user_tokens_with_old_holdings(db=db)


    for user_token in matching_user_tokens:
        holding = get_relevant_old_holding_by_user_id(db=db, user_id=user_token.user_id)


        push_title = f'🔁 {holding.instrument.name} - invest again'
        push_body = f'You haven\'t invested in {holding.instrument.name} for over a month. Invest a little money regularly to take advantage of the market!'
        
        print(push_title, push_body)

        if user_token.provider == 'EXPO':
            send_push(
                db=db,
                user_id=user_token.user_id,
                token_provider=user_token.provider,
                token_to=user_token.token,
                title=push_title,
                body=push_body,
                ttl=117800,
                androidChannelId='portfolio_updates',
                badge_no=1,
                is_sound_played=True
            )


if __name__ == '__main__':
    remind_invest_again()