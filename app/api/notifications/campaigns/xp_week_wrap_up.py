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


def notify_weekly_xp_wrap_up(db: Session):
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
    tokens = get_all_push_tokens(db=db)
    channelId = 'portfolio_updates'
    ttl = 172800

    for token in tokens:
        if token.provider == 'EXPO':
            if token.user.xp_current_week >= 50:
                title = "🏆 Overachiever!"
                message = f"You've earned +{token.user.xp_current_week} XP this week. Can you match it next week to stay at the top?"
            elif token.user.xp_current_week >= 10:
                title = "🏆 Up for a challenge?"
                message = f"You've earned +{token.user.xp_current_week} XP this week. You still have time for the final push to crush the competition. You in?"
            elif token.user.xp_current_week > 0:
                title = "🏆 Nice progress!"
                message = f"You've earned +{token.user.xp_current_week} XP this week. Let's make it 10 XP next week. You in?"
            else:
                title = "🏆 Every week counts"
                message = f"Everyone has a chance to climb to the top each week. Keep learning to crush it next week! You in?"

        print(token.user_id, title, message)

        r = send_push(
            db=db,
            user_id=token.user_id,
            token_provider=token.provider,
            token_to=token.token,
            title=title,
            body=message,
            androidChannelId=channelId,
            ttl=ttl,
            badge_no=1,
            is_sound_played=True
        )

        if r is False:
            print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
            crud.disable_push_token(db=db, provider=token.provider, token=token.token)
        else:
            print(f'OK User={token.user_id}, Token={token.token}')