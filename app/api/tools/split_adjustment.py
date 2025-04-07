import logging
import json
import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c


def find_eligible_holdings(db: Session, instrument_id: int) -> list:

    return db.query(models.Holding).\
        filter(models.Holding.instrument_id == instrument_id).\
        filter(models.Holding.date_last_updated < datetime.date.today()). \
        all()


def adjust_holding(db: Session, holding, multiplier: int) -> None:

    # upload the instruments to the database
    try:
        print(f"Portfolio ID: {holding.portfolio_id}, Instrument ID: {holding.instrument_id}, Quantity: {holding.quantity}, Price: {holding.average_price}")
        holding.quantity = holding.quantity * multiplier
        holding.average_price = holding.average_price / multiplier
        holding.date_last_updated = datetime.datetime.now()
        db.merge(holding)
        db.commit()

        crud.refresh_portfolio_stats(db=db, portfolio_id=holding.portfolio_id, refresh_timeout=0)
        
    except IntegrityError:
        print(f"Error Portfolio ID: {holding.portfolio_id}, Instrument ID: {holding.instrument_id}")
        db.rollback()
        raise

if __name__ == "__main__":
    
    db = SessionLocal()

    instrument_id = 118
    split_multiplier = 2

    # Find eligible holdings and adjust them
    eligible_holdings = find_eligible_holdings(db=db, instrument_id=instrument_id)
    for holding in eligible_holdings:
        adjust_holding(db=db, holding=holding, multiplier=split_multiplier)



    