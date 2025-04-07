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


def delete_instrument_by_id(db: Session, instrument_id):
    instrument_to_be_deleted = db.query(models.Instrument).\
        filter(models.Instrument.id == instrument_id).\
        first()
    
    db.delete(instrument_to_be_deleted)
    db.commit()

if __name__ == "__main__":
    
    db = SessionLocal()

    retired_instruments = find_retired_instruments(db=db)
    for retired_instrument in retired_instruments:
        print(retired_instrument.name, retired_instrument.holdings)
        if not retired_instrument.holdings:
            print('deleting the instrument', retired_instrument.id)
            delete_instrument_by_id(db=db, instrument_id=retired_instrument.id)
