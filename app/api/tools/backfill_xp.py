import logging
import json
import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c


def get_weekly_reset_cutover() -> datetime:
    now_utc = datetime.now(timezone.utc)
    last_monday = now_utc - timedelta(days=now_utc.weekday())
    cutover_date = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return cutover_date


def backdate_xp_by_user_id(db: Session, user_id: int, backfill_date: datetime, xp_amount: int, xp_reason: str, xp_detail: Optional[str]=None):
    # Create transaction
    transaction = models.XPTransaction(
        user_id=user_id,
        amount=xp_amount,
        reason=xp_reason,
        detail=xp_detail,
        date_credited=backfill_date,
    )
    db.add(transaction)

    # Get user object + increment XP stats
    user = crud.get_user_by_id(db=db, id=user_id)
    user.xp_total = models.User.xp_total + xp_amount
    if backfill_date >= get_weekly_reset_cutover():
        user.xp_current_week = models.User.xp_current_week + xp_amount
    db.merge(user)

    # Commit the changes
    db.commit()


def backdate_xp_on_buy_if_eligible(db: Session, transaction_id: int, backfill_date: datetime):
    transaction = crud.get_portfolio_transaction_by_id(db=db, id=transaction_id)
    if transaction is None:
        return False
    # c.XP_LIMIT.BUY_TRANSACTION_UNIQUE_ELIGIBLE_INSTRUMENTS

    date_24_hours_ago = backfill_date - timedelta(hours=24)
    n_unique_instruments = db \
        .query(models.PortfolioTransaction) \
        .distinct(models.PortfolioTransaction.associated_instrument_id) \
        .filter (
            # transactions executed that belong to the requester
            models.PortfolioTransaction.portfolio_id == transaction.portfolio_id,
            models.PortfolioTransaction.status == 'executed',
            models.PortfolioTransaction.date_executed != None,
            models.PortfolioTransaction.associated_instrument_id != None,
            models.PortfolioTransaction.transaction_type == models.PortfolioTransactionTypeUserScope.BUY.value,
            models.PortfolioTransaction.date_executed > date_24_hours_ago,
        ) \
        .count()

    if n_unique_instruments <= c.XP_LIMIT.BUY_TRANSACTION_UNIQUE_ELIGIBLE_INSTRUMENTS:
        user_id = transaction.portfolio.user_id
        backdate_xp_by_user_id(
            db=db,
            user_id=user_id,
            backfill_date=transaction.date_executed,
            xp_amount=c.XP_CREDIT.BUY_TRANSACTION,
            xp_reason=c.XP_REASON.BUY_TRANSACTION,
            xp_detail=f"TX={transaction.id}",
        )
        return True

    return False


def backdate_xp_on_sell_if_eligible(db: Session, transaction_id: int, backfill_date: datetime):
    transaction = crud.get_portfolio_transaction_by_id(db=db, id=transaction_id)
    if transaction is None:
        return False
 
    ex_avg_price = transaction.ex_avg_price
    sale_price = transaction.value / transaction.quantity
    gain = math.floor((sale_price - ex_avg_price) * transaction.quantity)
    if gain > 0:
        user_id = transaction.portfolio.user_id
        xp_amount = c.XP_CREDIT.COLLECT_PROFIT * gain
        backdate_xp_by_user_id(
            db=db,
            user_id=user_id,
            backfill_date=transaction.date_executed,
            xp_amount=xp_amount,
            xp_reason=c.XP_REASON.SELL_ASSET_AT_PROFIT,
            xp_detail=f"TX={transaction.id}"
        )

    return False


def get_all_users(db: Session) -> list:
    """
    Find all users 
    """
    return db \
        .query(models.User) \
        .order_by(models.User.id) \
        .all()


def get_all_users_sorted_by_xp(db: Session) -> list:
    """
    Find all users 
    """
    return db \
        .query(models.User) \
        .order_by(models.User.xp_total.asc()) \
        .all()

def get_portfolio_holdings(db: Session, portfolio_id: int) -> list:
    """
    Find all holdings for a user
    """
    return db \
        .query(models.Holding) \
        .filter(models.Holding.portfolio_id == portfolio_id) \
        .order_by(models.Holding.id) \
        .all()


def get_all_executed_transactions(db: Session) -> list:
    """
    Find all transactions for a user
    """
    return db \
        .query(models.PortfolioTransaction) \
        .filter(models.PortfolioTransaction.status == "executed") \
        .order_by(models.PortfolioTransaction.id) \
        .all()


def get_executed_transactions(db: Session, portfolio_id: int) -> list:
    """
    Find all transactions for a user
    """
    return db \
        .query(models.PortfolioTransaction) \
        .filter(models.PortfolioTransaction.portfolio_id == portfolio_id) \
        .filter(models.PortfolioTransaction.status == "executed") \
        .order_by(models.PortfolioTransaction.id) \
        .all()


def get_portfolios(db: Session) -> list:
    """
    Get all portfolios
    """
    return db \
        .query(models.Portfolio) \
        .all()


def process_signup(db: Session, user_id: int):
    print(f"XP/Signup: user {user_id}")
    user = crud.get_user_by_id(db=db, id=user_id)
    backdate_xp_by_user_id(
        db=db,
        user_id=user.id,
        backfill_date=user.date_created,
        xp_amount=c.XP_CREDIT.SIGNUP,
        xp_reason=c.XP_REASON.SIGNUP,
        xp_detail=None
    )


def process_skills(db: Session, user_id: int):
    print(f"XP/Skills: user {user_id}")
    unlocked_skills = db \
        .query(models.UserSkill) \
        .filter(
            models.UserSkill.date_last_unlocked != None,
            models.UserSkill.user_id == user_id,
        ) \
        .all()

    for user_skill in unlocked_skills:
        print(f"XP/Skills: User={user_id}, Skill={user_skill.skill_id}")
        backdate_xp_by_user_id(
            db=db,
            user_id=user_id,
            backfill_date=user_skill.date_last_unlocked,
            xp_amount=c.XP_CREDIT.UNLOCK_SKILL,
            xp_reason=c.XP_REASON.UNLOCK_SKILL,
            xp_detail=f"SKL={user_skill.skill_id}"
        )


def process_transaction(db: Session, transaction_id: int):
    transaction = crud.get_portfolio_transaction_by_id(db=db, id=transaction_id)
    
    if transaction.transaction_type == models.PortfolioTransactionTypeAppScope.BUY.value:
        print(f"XP/Transaction/Buy: Transaction={transaction.id}")
        backdate_xp_on_buy_if_eligible(
            db=db,
            transaction_id=transaction.id,
            backfill_date=transaction.date_executed
        )
    elif transaction.transaction_type == models.PortfolioTransactionTypeAppScope.SELL.value:
        print(f"XP/Transaction/Sell: Transaction={transaction.id}")
        backdate_xp_on_sell_if_eligible(
            db=db,
            transaction_id=transaction.id,
            backfill_date=transaction.date_executed
        )
    else:
        print(f"XP/Transaction/Reward: Transaction={transaction.id}")
        backdate_xp_by_user_id(
            db=db,
            user_id=transaction.portfolio.user_id,
            backfill_date=transaction.date_executed,
            xp_amount=c.XP_CREDIT.COLLECT_REWARD,
            xp_reason=c.XP_REASON.COLLECT_REWARD,
            xp_detail=f"TX={transaction.id}"
        )


def recalc_ex_avg_price_by_portfolio_id(db: Session, portfolio_id: int):
    print(f"XP/RecalcExAvgPrice: Portfolio={portfolio_id}")
    holdings = {}

    for transaction in get_executed_transactions(db=db, portfolio_id=portfolio_id):

        if transaction.transaction_type == 'buy':
            print(f"XP/RecalcExAvgPrice: BUY: Portfolio={portfolio_id}, Transaction={transaction.id}")
            current_holding = holdings.get(transaction.associated_instrument_id, {"book_value": 0, "shares": 0})
            holdings[transaction.associated_instrument_id] = {
                "shares": current_holding["shares"] + transaction.quantity,
                "book_value": current_holding["book_value"] + transaction.value
            }
        elif transaction.transaction_type == 'sell':
            print(f"XP/RecalcExAvgPrice: SELL: Portfolio={portfolio_id}, Transaction={transaction.id}")
            current_holding = holdings.get(transaction.associated_instrument_id, {"book_value": 0, "shares": 0})
            ex_avg_price = (current_holding["book_value"] / current_holding["shares"]) if current_holding["shares"] > 0 else None
            post_sale_holding = {
                "shares": current_holding["shares"] - transaction.quantity,
                "book_value": current_holding["book_value"] - transaction.value
            }
            if post_sale_holding["shares"] < 0:
                post_sale_holding = {"book_value": 0, "shares": 0}
            holdings[transaction.associated_instrument_id] = {
                "shares": post_sale_holding["shares"],
                "book_value": post_sale_holding["book_value"]
            }
            transaction.ex_avg_price = ex_avg_price
            db.merge(transaction)
            db.commit()


def reset_users_xp(db: Session):
    db \
        .query(models.User) \
        .update({
            models.User.xp_current_week: 0,
            models.User.xp_total: 0
        })
    db.commit()


def reset_xp_transactions(db: Session):
    db.query(models.XPTransaction).delete()
    db.commit()

if __name__ == "__main__":
    
    db = SessionLocal()

    """
    prep:
    step 1: reset user's weekly and total xp
    step 2: clean the XP transactions
    step 3: recalculate ex_avg_price for sell portfolio_transaction (use audit code)
    """

    print(f"XP/ResetUserXP")
    reset_users_xp(db=db)

    print(f"XP/ResetTransactions")
    reset_xp_transactions(db=db)

    print(f"XP/CalculateExAvgPrice")
    for portfolio in get_portfolios(db=db):
        recalc_ex_avg_price_by_portfolio_id(db=db, portfolio_id=portfolio.id)

    """
    then, for each use
    step 4: credit XP for sign-ups
    step 5: credit XP for skills
    step 6: credit XP for transactions
      a. buy
      b. sell at profit
      c. bonus
    """
    users = get_all_users(db=db)
    for user in users:
        process_signup(db=db, user_id=user.id)
        process_skills(db=db, user_id=user.id)
        
    transactions = get_all_executed_transactions(db=db)
    for transaction in transactions:
        process_transaction(db=db, transaction_id=transaction.id)

    print("Completed!")
    users = get_all_users_sorted_by_xp(db=db)
    for user in users:
        if user.xp_total > 0:
            print(f"User={user.id}, XP_Total={user.xp_total}, XP_Current_Week={user.xp_current_week}")
