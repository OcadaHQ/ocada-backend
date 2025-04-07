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


def get_all_push_tokens(db: Session) -> list:
    return db \
    .query(models.UserPushToken) \
    .filter(models.UserPushToken.status == 'active') \
    .order_by(models.UserPushToken.user_id.asc()) \
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

def get_recent_push_tokens(db: Session) -> list:
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

def get_all_shareholders_tokens(db: Session, instrument_id: int):
    return db \
    .query(models.UserPushToken) \
    .join(models.Portfolio, models.Portfolio.user_id == models.UserPushToken.user_id) \
    .join(models.Holding, models.Portfolio.id == models.Holding.portfolio_id) \
    .filter(
        or_(
            models.Portfolio.user_id == 2,
            models.Holding.instrument_id == instrument_id
        )
    ) \
    .filter(models.UserPushToken.status == 'active') \
    .order_by(models.UserPushToken.user_id.asc()) \
    .all()

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



def notify_users_eligible_for_weekly_reward(db: Session):
    tokens = get_push_tokens_by_weekly_bonus(db=db)
    ttl = 172800
    title = '🔓 Reward unlocked'
    message = 'Open the app to collect your weekly reward'

    for token in tokens:

        if token.provider == 'EXPO':


            print(token.user_id)

            r = send_push(
                db=db,
                user_id=token.user_id,
                token_provider=token.provider,
                token_to=token.token,
                title=title,
                body=message,
                androidChannelId='rewards',
                ttl=ttl,
                badge_no=1,
                is_sound_played=True
            )

            if r is False:
                print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                crud.disable_push_token(db=db, provider=token.provider, token=token.token)
            else:
                print(f'OK User={token.user_id}, Token={token.token}')


def notify_reengage(db: Session):
    tokens = get_all_push_tokens(db=db)
    ttl = 172800

    for token in tokens:

       
        if len(token.user.portfolios) > 0:
            portfolio = token.user.portfolios[0]
            gain_formatted = round(portfolio.stats.total_gain, 1) if portfolio.stats.total_gain < 1 else round(portfolio.stats.total_gain)
            gain_perc = round(portfolio.stats.total_gain/portfolio.stats.total_net_worth*100, 2)
            cash_balance = round(token.user.portfolios[0].cash_balance)

            if gain_perc > 1:
                title = f'🚀 You\'ve made ${gain_formatted}!'
                message = f'Take 5 minutes NOW to invest more!' # and complete a lesson!'
            else:
                title = '👟 Nike up 8% this week'
                message = f'Nike reports strong direct-to-consumer sales despite challenges its competitors are facing. '

            print(title, message)
            # continue

            # if portfolio.date_last_updated < datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30):
            #     # title = f'💵 Let\'s learn to invest!'
            #     if gain_perc > 0:
            #         title = f'💥 You\'re up ${gain_formatted}!'
            #         message = f'Keep investing and take 5 minutes now to complete a lesson!'
            #     # elif gain_perc >= 0:
            #     #     message = f'Your portfolio is STRRRONG! It\'s been over a month, and you should invest more!'
            #     else:
            #         title = '📈 NVIDIA rise!'
            #         message = f'Investors gain confidence in the resilience of the US economy.'

            # elif portfolio.date_last_updated < datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7):
            #     # title = f'💵 Let\'s learn to invest!'
            #     if gain_perc > 0:
            #         title = f'💥 You\'re up ${gain_formatted}!'
            #         message = f'Keep investing and take 5 minutes now to complete a lesson!'
            #     # elif gain_perc >= 0:
            #     #     message = f'Your portfolio is STRRRONG! It\'s been over a week, and you should keep investing to learn!'
            #     else:
            #         title = '📈 Stocks rise!'
            #         message = f'Investors gain confidence in the resilience of the US economy.'
            # elif portfolio.date_last_updated < datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1):
            #     # title = f'💵 Let\'s learn to invest!'
            #     if gain_perc > 0:
            #         title = f'💥 You\'re up ${gain_formatted}!'
            #         message = f'Keep investing and take 5 minutes now to complete a lesson!'
            #     # elif gain_perc >= 0:
            #     #     message = f'Your portfolio is STRRRONG! It\'s been over a week, and you should keep investing to learn.'
            #     else:
            #         title = '📈 Stocks rise!'
            #         message = f'Investors gain confidence in the resilience of the US economy.'
            # else:
            # # portfolio.date_last_updated < datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=18):
                
            #     if gain_perc > 0:
            #         title = f'💥 You\'re up ${gain_formatted}!'
            #         message = f'Keep investing and take 5 minutes now to complete a lesson!'
            #     # elif gain_perc >= 0:
            #     #     message = f'Your portfolio is strong! Keep investing to learn!'
            #     else:
            #         title = '📈 Stocks rise!'
            #         message = f'Investors gain confidence in the resilience of the US economy.'
            
            print(f"user={token.user_id}", title, message)
            # continue

            r = send_push(
                db=db,
                user_id=token.user_id,
                token_provider=token.provider,
                token_to=token.token,
                title=title,
                body=message,
                ttl=ttl,
                androidChannelId='portfolio_updates',
                badge_no=2,
                is_sound_played=True
            )

            if r is False:
                print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                crud.disable_push_token(db=db, provider=token.provider, token=token.token)
            else:
                print(f'OK User={token.user_id}, Token={token.token}')


def notify_portfolio_update(db: Session):
    tokens = get_all_push_tokens(db=db)
    ttl = 172800

    for token in tokens:

       
        if len(token.user.portfolios) > 0:
            portfolio = token.user.portfolios[0]
            gain_perc = round(portfolio.stats.total_gain/portfolio.stats.total_net_worth*100, 2)
            cash_balance = round(token.user.portfolios[0].cash_balance)

            title = f'🔥 Last chance to invest'

            if gain_perc > 0:
                message = f'You\'re up {gain_perc}%. Invest today before the markets close tomorrow due to Easter'
            else:
                message = f'Invest today before the markets close tomorrow due to Easter'

            print(f"user={token.user_id}", title, message)
            # continue

            r = send_push(
                db=db,
                user_id=token.user_id,
                token_provider=token.provider,
                token_to=token.token,
                title=title,
                body=message,
                ttl=ttl,
                androidChannelId='portfolio_updates',
                badge_no=1,
                is_sound_played=True
            )

            if r is False:
                print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                crud.disable_push_token(db=db, provider=token.provider, token=token.token)
            else:
                print(f'OK User={token.user_id}, Token={token.token}')



def notify_all_users_announcement(db: Session):
    tokens = get_all_push_tokens(db=db)
    ttl = 172800
    title = '🆕 8 new stocks!'


    for token in tokens:

        if len(token.user.portfolios) > 0:
            portfolio = token.user.portfolios[0]
            char_name = portfolio.name
            message = f"Coinbase, Virgin Galactic and other six stocks have just launched on Snips. Take advantage of the rising bull market!"


            print(message)
            # continue
            if token.provider == 'EXPO':
                r = send_push(
                    db=db,
                    user_id=token.user_id,
                    token_provider=token.provider,
                    token_to=token.token,
                    title=title,
                    body=message,
                    ttl=ttl,
                    androidChannelId='app_updates',
                    badge_no=1,
                    is_sound_played=True
                )

                if r is False:
                    print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                    crud.disable_push_token(db=db, provider=token.provider, token=token.token)
                else:
                    print(f'OK User={token.user_id}, Token={token.token}')


def notify_non_premium(db: Session):
    tokens = get_all_push_tokens(db=db)
    ttl = 172800
    title = "💎 Imagine no subscriptions"
    message = f"Premium is now for life! Get all the goodies forever, without any subscriptions."

    for token in tokens:
        if token.user.is_premium == 0:

            print(token.user_id, title, message)
            # continue
            if token.provider == 'EXPO':
                r = send_push(
                    db=db,
                    user_id=token.user_id,
                    token_provider=token.provider,
                    token_to=token.token,
                    title=title,
                    body=message,
                    ttl=ttl,
                    androidChannelId='promos',
                    badge_no=69420,
                    is_sound_played=True
                )

                if r is False:
                    print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                    crud.disable_push_token(db=db, provider=token.provider, token=token.token)
                else:
                    print(f'OK User={token.user_id}, Token={token.token}')


def notify_promo_discount(db: Session):
    tokens = get_all_push_tokens(db=db)
    ttl = 172800
    title = "💥 Easter sale: 40% off"


    for token in tokens:

        if len(token.user.portfolios) > 0:
            portfolio = token.user.portfolios[0]
            char_name = portfolio.name
            message = f"This weekend only: 40% off a year of Premium!"

            print(token.user_id, title, message)
            if token.provider == 'EXPO':
                r = send_push(
                    db=db,
                    user_id=token.user_id,
                    token_provider=token.provider,
                    token_to=token.token,
                    title=title,
                    body=message,
                    ttl=ttl,
                    androidChannelId='promos',
                    badge_no=1,
                    is_sound_played=True
                )

                if r is False:
                    print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                    crud.disable_push_token(db=db, provider=token.provider, token=token.token)
                else:
                    print(f'OK User={token.user_id}, Token={token.token}')


def notify_individually(db: Session, user_id: int, title: str, message: str):
    tokens = db \
    .query(models.UserPushToken) \
    .filter(models.UserPushToken.status == 'active') \
    .filter(models.UserPushToken.user_id == user_id) \
    .all()

    ttl = 172800
    for token in tokens:
        if token.provider == 'EXPO':
            r = send_push(
                db=db,
                user_id=token.user_id,
                token_provider=token.provider,
                token_to=token.token,
                title=title,
                body=message,
                ttl=ttl,
                badge_no=1,
                is_sound_played=True
            )

            if r is False:
                print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                crud.disable_push_token(db=db, provider=token.provider, token=token.token)
            else:
                print(f'OK User={token.user_id}, Token={token.token}')


def notify_lesson_reminder(db: Session):
    tokens = get_all_push_tokens(db=db)
    ttl = 172800

    n_lessons_total = db \
        .query(func.count(models.Lesson.id)) \
        .scalar()
    
    
    for token in tokens:

        n_lessons_completed_by_user = db \
            .query(func.count(models.UserLesson.lesson_id)) \
            .filter(models.UserLesson.user_id == token.user_id) \
            .scalar()
        n_lesson_uncompleted_by_user = n_lessons_total - n_lessons_completed_by_user

        if n_lesson_uncompleted_by_user == 0:
            continue

        if len(token.user.portfolios) > 0:
            portfolio = token.user.portfolios[0]
            char_name = portfolio.name
            title = f"👋 Hi {char_name}"
            message = f"It's time for your daily Snips lesson. Take 5 minutes now to complete it."
            
            print(title, message)
            
            if token.provider == 'EXPO':
                r = send_push(
                    db=db,
                    user_id=token.user_id,
                    token_provider=token.provider,
                    token_to=token.token,
                    title=title,
                    body=message,
                    ttl=ttl,
                    androidChannelId='new_skills',
                    badge_no=4,
                    is_sound_played=True
                )

                if r is False:
                    print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                    crud.disable_push_token(db=db, provider=token.provider, token=token.token)
                else:
                    print(f'OK User={token.user_id}, Token={token.token}')


def notify_stock_news(db: Session):
    tokens = get_all_push_tokens(db=db)
    title = '🍎 Apple disappointed'
    message = f'New iPhone offers little innovation over old models. Apple stock falls this week on investor concerns over weak demand.'
    channelId = 'portfolio_updates'
    ttl = 172800

    for token in tokens:
        if token.provider == 'EXPO':
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


def notify_premium_ab(db: Session, is_even_user_id: int = True):
    tokens = get_all_push_tokens(db=db)
    title = "🎁 You're Premium"
    message = "Enjoy FREE Premium for 3 days. No payment required"
    channelId = 'account_alerts'
    ttl = 172800

    for token in tokens:
        if token.provider == 'EXPO' and token.user_id % 2 != 0:
            if token.user.is_premium != 1:
                continue

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


def notify_premium_end_ab(db: Session, is_even_user_id: int = True):
    tokens = get_all_push_tokens(db=db)
    title = "✅ Enjoyed your free Premium?"
    message = "Support our mission and get extra perks for only $9.99 a year"
    channelId = 'account_alerts'
    ttl = 172800

    for token in tokens:
        if token.provider == 'EXPO' and token.user_id % 2 == 0:
            if token.user.is_premium == 1 or token.user_id > 2734:
                continue

            # print(token.user_id)
            # continue
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


def notify_premium_thanks(db: Session, user_id: int):
    title = "🎁 Your Premium reward"
    message = "We've credited 5000 coins as a thank you for trying Snips Premium 🤗 here's to your success!"
    notify_individually(db=db, user_id=user_id, title=title, message=message)


def notify_lapsed_premium(db: Session, user_id: int):
    title = "🎁 You're Premium"
    message = "Thanks for giving Snips another shot! We've activated your FREE Premium until 6th Feb. It won't automatically renew and you won't be charged"
    notify_individually(db=db, user_id=user_id, title=title, message=message)


def notify_premium_billing_error(db: Session, user_id: int):
    title = "⚠️ Billing issue"
    message = "Thanks for trying Snips Premium! We noticed a billing issue when you attempted to renew Premium. Please validate your payment details in the App Store"
    notify_individually(db=db, user_id=user_id, title=title, message=message)


def notify_players_with_weekly_xp(db: Session):
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
                message = f"You can always climb to the top. Invest in stocks and complete quizzes to crush it next week! You in?"

        print(token.user_id, title, message)
        # continue

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
            

def notify_by_app_version(db: Session, version_id: str):
    tokens = get_all_push_tokens(db=db)
    title = "✅ Ask AI"
    message = "Make smart decisions by asking Snips AI. Open the app to use AI Chat for free!"
    channelId = 'app_updates'
    ttl = 172800

    users_notified = []

    for token in tokens:
        if token.provider == 'EXPO':
            if token.user.last_seen_app_version == version_id:
                users_notified.append(token.user_id)
                # continue
                r = send_push(
                    db=db,
                    user_id=token.user_id,
                    token_provider=token.provider,
                    token_to=token.token,
                    title=title,
                    body=message,
                    ttl=ttl,
                    androidChannelId=channelId,
                    badge_no=69,
                    is_sound_played=True
                )

                if r is False:
                    print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                    crud.disable_push_token(db=db, provider=token.provider, token=token.token)
                else:
                    print(f'OK User={token.user_id}, Token={token.token}')

    print(users_notified)


def notify_outdated_abc(db: Session, version_id: str):
    tokens = get_all_push_tokens(db=db)
    title = "🙌 Update me"
    message = "Update Snips on the app store to get the AI to do investing research for you!"
    channelId = 'app_updates'
    ttl = 172800

    users_notified = []

    for token in tokens:
        if token.provider == 'EXPO':
            if token.user_id == 2 or (token.user.last_seen_app_version != version_id and token.user_id % 3 == 0):
                users_notified.append(token.user_id)
                # continue
                r = send_push(
                    db=db,
                    user_id=token.user_id,
                    token_provider=token.provider,
                    token_to=token.token,
                    title=title,
                    body=message,
                    ttl=ttl,
                    androidChannelId=channelId,
                    badge_no=1,
                    is_sound_played=True
                )

                if r is False:
                    print(f'FAIL User={token.user_id}, Token={token.token}, token will be disabled')
                    crud.disable_push_token(db=db, provider=token.provider, token=token.token)
                else:
                    print(f'OK User={token.user_id}, Token={token.token}')

    print(users_notified)


if __name__ == "__main__":
    
    db = SessionLocal()
    # notify_non_premium(db=db)
    # configure notification channels!
    # notify_users_eligible_for_weekly_reward(db=db)
    notify_reengage(db=db)
    # notify_stock_news(db=db)
    # notify_lesson_reminder(db=db)
    # notify_portfolio_update(db=db)
    # notify_premium_billing_error(db=db, user_id=1026)
    # notify_all_users_announcement(db=db)
    # notify_premium_end_ab(db=db)
    # notify_by_app_version(db=db, version_id='1.19.0')
    # notify_outdated_abc(db=db, version_id='1.19.0')

    # title = "💎 Imagine no subscriptions"
    # message = f"Premium is now for life! Get all the goodies forever, without any subscriptions."
    
    # notify_individually(db=db, user_id=2, title=title, message=message)
    # notify_portfolio_update(db=db)
    # notify_shareholders(db=db)
