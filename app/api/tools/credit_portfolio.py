import logging
import json
import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c


def find_eligible_users(db: Session) -> list:
    """
    Find all users that are eligible for a credit.
    Criteria:
        - User is active
        - User account created last week or earlier
        - User account last active last monday or later
        - Not active now: user has not been credited in the last week
    """

    return db.query(models.User).\
        filter(models.User.status == 'active').\
        filter(models.User.date_last_active >= datetime.date(2022, 9, 12)). \
        filter(models.User.date_created < datetime.date.today()). \
        all()


def credit_portfolio(db: Session, portfolio_id: int, quantity: float) -> None:
    try:
        
        transaction = models.PortfolioTransaction(
            portfolio_id=portfolio_id,
            associated_instrument_id=None,
            transaction_type='REWARD_PROMO',
            quantity=quantity,
            value=quantity,
            status='executed',
            date_executed=datetime.datetime.now(),
        )

        portfolio = crud.get_portfolio_by_id(db, portfolio_id)
        portfolio.cash_balance += quantity
        db.add(transaction)
        db.merge(portfolio)
        db.commit()

        crud.refresh_portfolio_stats(db=db, portfolio_id=portfolio_id, refresh_timeout=0)
        
    except IntegrityError:
        db.rollback()
        raise

if __name__ == "__main__":
    
    db = SessionLocal()
    exit()

    credit_amount = 0.0
    portfolio_id = 0

    credit_portfolio(
        db=db,
        portfolio_id=portfolio_id,
        quantity=credit_amount
    )

    # Find active users
    # Active user is a user who logged in within the last week and with account age more than one day

    # For each user, credit $500 to their account
    # Create a transaction for each user
    # Update the portfolio balance
    # Mark transaction as executed

    # eligible_users = find_eligible_users(db=db)
    # for user in eligible_users:
    #     for portfolio in user.portfolios:
    #         credit_portfolio(db=db, portfolio_id=portfolio.id, quantity=credit_amount)
