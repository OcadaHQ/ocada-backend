import os
from fastapi_login import LoginManager
from app.api.database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


auth_secret = os.getenv("APP_AUTH_SECRET", None)
manager = LoginManager(auth_secret, '/users')
