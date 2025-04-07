import logging
import json
import datetime

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c


def find_retired_instruments(db: Session) -> list:
    return db.query(models.Instrument).\
        filter(models.Instrument.status == 'retired').\
        all()

def find_eligible_holdings(db: Session, instrument_id: int) -> list:

    return db.query(models.Holding).\
        filter(models.Holding.instrument_id == instrument_id).\
        filter(models.Holding.quantity > 0).\
        all()

def sell_off_holding_by_id(db: Session, holding):
    print(holding.quantity)
    try:
        transaction = crud.create_transaction(
            db=db,
            portfolio_id=holding.portfolio_id,
            associated_instrument_id=holding.instrument_id,
            transaction_type=models.PortfolioTransactionTypeUserScope.SELL.value,
            quantity=holding.quantity
        )
        transaction = crud.execute_portfolio_transaction(db=db, id=transaction.id)
        crud.credit_xp_on_sell_if_eligible(
            db=db,
            transaction_id=transaction.id
        )
        return transaction
    except SQLAlchemyError:
        print(f"Error SELL Portfolio ID: {holding.portfolio_id}, Instrument ID: {holding.instrument_id}")
        db.rollback()
        raise

def rebuy_instrument_by_id(db: Session, portfolio_id: int, instrument_id: int, quantity: float):
    try:
        transaction = crud.create_transaction(
            db=db,
            portfolio_id=portfolio_id,
            associated_instrument_id=instrument_id,
            transaction_type=models.PortfolioTransactionTypeUserScope.BUY.value,
            quantity=quantity
        )
        transaction = crud.execute_portfolio_transaction(db=db, id=transaction.id)
        return transaction
    except SQLAlchemyError:
        print(f"Error BUY Portfolio ID: {portfolio_id}, Instrument ID: {instrument_id}")
        db.rollback()
        raise
    

if __name__ == "__main__":
    
    db = SessionLocal()


    # instrument_retired_id = 366 # TWTR
    # instrument_heir_id = 387 # GOOGL

    # instrument_heir = crud.get_instrument_by_id(
    #     db=db,
    #     id=instrument_heir_id
    #     )

    # print(instrument_heir.kpi_latest_price.price)

    # find all holdings > 0
    # sell the holding (instrument_retired_id), keep the $amount in mind
    # buy instrument_heir_id $amount/latest_price

    retired_instruments = find_retired_instruments(db=db)
    
    for retired_instrument in retired_instruments:
    # Find eligible holdings and adjust them
        print('processing: ', retired_instrument.id, retired_instrument.name)
        eligible_holdings = find_eligible_holdings(db=db, instrument_id=retired_instrument.id)

        for holding in eligible_holdings:
            portfolio_id = holding.portfolio_id
            sell_transaction = sell_off_holding_by_id(db=db, holding=holding)
            print(sell_transaction.id, sell_transaction.value)


        # buy_transaction = rebuy_instrument_by_id(
        #     db=db,
        #     portfolio_id=portfolio_id,
        #     instrument_id=instrument_heir_id,
        #     quantity=sell_transaction.value / instrument_heir.kpi_latest_price.price,
        # )

            
