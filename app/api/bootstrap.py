import logging
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.database import engine, SessionLocal
from app.models import models
import app.api.constants as c


def bootstrap_instruments(db: Session, bootstrap_file: str) -> None:
    """
    Bootstrap the database with the instruments.
    Should only be run once to set up the database.
    """

    # import the instruments from a JSON file
    try:
        
        with open(bootstrap_file, 'r') as f:
            instruments = json.load(f)
    except FileNotFoundError:
        print("Could not find bootstrap file: instruments.")
        raise

    # upload the instruments to the database
    try:
        
        for instrument in instruments['data']:
            db.add(models.Instrument(
                type=instrument['type'],
                symbol=instrument['symbol'],
                name=instrument['name'],
            ))

        db.commit()
    except IntegrityError:
        db.rollback()
        raise


def bootstrap_characters(db: Session, bootstrap_file: str) -> None:
    """
    Bootstrap the database with characters.
    Should only be run once to set up the database.
    """

    # import character icons from a JSON file
    try:
        
        with open(bootstrap_file, 'r') as f:
            characters = json.load(f)
    except FileNotFoundError:
        print("Could not find bootstrap file: characters.")
        raise

    # upload the instruments to the database
    try:
        
        for character in characters['data']:
            db.add(models.Character(
                image_url=character['image_url'],
                category=character['category'],
            ))

        db.commit()
    except IntegrityError:
        db.rollback()
        raise

if __name__ == "__main__":
    
    db = SessionLocal()
    logging.info("Create tables")
    models.Base.metadata.create_all(bind=engine)

    logging.info("Add instruments")
    bootstrap_instruments(
        db=db,
        bootstrap_file=c.BOOTSTRAP_FILE_INSTRUMENTS
    )

    logging.info("Add characters")
    bootstrap_characters(
        db=db,
        bootstrap_file=c.BOOTSTRAP_FILE_CHARACTERS
    )
