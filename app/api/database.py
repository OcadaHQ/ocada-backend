import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv("APP_ENVIRONMENT", "dev")
DB_HOST = os.getenv("APP_DB_HOST")
DB_PORT = os.getenv("APP_DB_PORT")
DB_USER = os.getenv("APP_DB_USER")
DB_PASSWORD = os.getenv("APP_DB_PASSWORD")
DB_NAME  = os.getenv("APP_DB_NAME")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create the database enine
logger.info("Create the database engine")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args={"check_same_thread": False} # only required for sqlite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
