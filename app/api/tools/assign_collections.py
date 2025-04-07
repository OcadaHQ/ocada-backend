import logging
import json
import datetime

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api import crud
from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c

# pepe: filter(models.Instrument.name.ilike(f"%pepe%")).\
# memes: filter(models.Instrument.tags.ilike(f"%memes%")).\
# cats: filter(models.Instrument.tags.ilike(f"%cat-themed%")).\
# dogs: filter(models.Instrument.tags.ilike(f"%doggone-doggerel%")).\
# gaming: filter(models.Instrument.tags.ilike(f"%gaming%")).\
# defi: filter(or_(models.Instrument.tags.ilike(f"%defi%")),models.Instrument.tags.ilike(f"%dex%")).\
# ai: filter(models.Instrument.name.like(f"%AI%")).\

def get_instruments(db: Session) -> list:
    return db.query(models.Instrument).\
        filter(models.Instrument.status == 'active').\
        filter(models.Instrument.name.like(f"%AI%")).\
        all()

def get_instruments_by_cap(db: Session, cap_over: int) -> list:
    return db.query(models.Instrument).\
        join(models.InstrumentKPI_TokenMetrics).\
        filter(models.Instrument.status == 'active').\
        filter(models.InstrumentKPI_TokenMetrics.market_cap >= cap_over).\
        all()

def assign_instrument_to_collection(db: Session, instrument_id: int, collection_id: int):
    membership = models.InstrumentCollectionMembership(
        collection_id=collection_id,
        instrument_id=instrument_id
    )
    db.merge(membership)
    db.commit()


if __name__ == "__main__":
    
    db = SessionLocal()

    collection_id = 14
    matched_instruments = get_instruments(db=db)
    for instrument in matched_instruments:
        print(instrument.name, instrument.id)
        assign_instrument_to_collection(db=db, instrument_id=instrument.id, collection_id=collection_id)
        