import logging
import json
import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c


def get_all_users(db: Session) -> list:
    """
    Find all users 
    """
    return db.query(models.User).all()

def get_portfolio_holdings(db: Session, portfolio_id: int) -> list:
    """
    Find all holdings for a user
    """
    return db \
        .query(models.Holding) \
        .filter(models.Holding.portfolio_id == portfolio_id) \
        .order_by(models.Holding.id) \
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



def recalculate_transactions(db: Session, portfolio_id: int):
    cash_balance = 1000.0
    cash_correction = 0
    holdings = {}
    for transaction in get_executed_transactions(db=db, portfolio_id=portfolio_id):
        # print(f"[{transaction.id}:A] ${cash_balance} / {holdings.get(transaction.associated_instrument_id, 0)}")
        if transaction.transaction_type == 'buy':
            current_holding_quantity = holdings.get(transaction.associated_instrument_id, 0)
            cash_balance -= transaction.value
            holdings[transaction.associated_instrument_id] = current_holding_quantity + transaction.quantity
        elif transaction.transaction_type == 'sell':
            current_holding_quantity = holdings.get(transaction.associated_instrument_id, 0)
            new_quantity = current_holding_quantity - transaction.quantity
            transaction_value = transaction.value
            sell_price = transaction.value/transaction.quantity
            if new_quantity < 0:
                abs_new_quantity = abs(new_quantity)
                transaction_error_value = abs_new_quantity * sell_price
                new_quantity = 0
                transaction_value -= transaction_error_value
                cash_correction += transaction_error_value
                print(transaction.quantity - abs_new_quantity)
                # transaction.quantity = transaction.quantity - abs_new_quantity
                # transaction.value = transaction_value
                # db.merge(transaction)
                # db.commit()

            cash_balance += transaction_value
            holdings[transaction.associated_instrument_id] = new_quantity


        
            
        elif transaction.transaction_type in ['bonus', 'REWARD_WEEKLY', 'REWARD_DAILY']:
            cash_balance += transaction.value


        # print(f"[{transaction.id}:B] ${cash_balance} / {holdings.get(transaction.associated_instrument_id, 0)}")
        # for holding_value in holdings.values():
        #     if holding_value < 0:
        #         print(transaction.id)
        #         exit()

        # if cash_balance < 0:
        #     print(transaction.id)
        #     exit()

    # print(holdings, cash_balance, cash_correction)

    if cash_correction > 0:
        return cash_correction
    return False

if __name__ == "__main__":
    
    db = SessionLocal()


    # recalculate_transactions(db=db, portfolio_id=2)

    # Find eligible users and credit their portfolios
    users = get_all_users(db=db)
    for user in users:
        for portfolio in user.portfolios:
            correction = recalculate_transactions(db=db, portfolio_id=portfolio.id)
            if correction:
                print(portfolio.id, portfolio.name, correction, portfolio.date_last_updated)






# get combination of portflio+instrument
# get all transactions for that combination
# accumulate buy transactions until hit sell transaction
# if sell transaction makes buy accumulator 
# recalculate sell transaction and update