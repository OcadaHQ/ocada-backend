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


def announce_instrument_news():
    """
    TBD
    """
    db: Session = SessionLocal()


if __name__ == '__main__':
    pass