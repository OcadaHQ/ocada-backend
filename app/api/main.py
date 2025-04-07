import logging
import logging.config
import os

from fastapi import FastAPI, Query, Path, HTTPException, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.exceptions import SnipsError
from app.api.database import engine, SessionLocal
from app.api import crud
from app.models import api_schema, models
import app.api.constants as c

from app.api.routers import \
    characters as r_characters, \
    instruments as r_instruments, \
    users as r_users, \
    portfolios as r_portfolios, \
    skills as r_skills, \
    social as r_social, \
    learn as r_learn, \
    conversations as r_conversations 

# set up logging
logging.config.fileConfig(fname='app/api/data/logging.conf',
                          disable_existing_loggers=False)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ocada API",
    description="Ocada: artificial intelligence for blockchain",
    terms_of_service="http://api.ocada.ai/static/policies/terms.pdf",
    version=c.API_VERSION,
    contact={
        "name": "Ocada",
        "url": "https://ocada.ai"
    },
    # hide docs in production 
    docs_url= None if os.getenv("APP_ENVIRONMENT") == 'prod' else '/docs',
    redoc_url = None if os.getenv("APP_ENVIRONMENT") == 'prod' else '/redoc',
    openapi_url = None if os.getenv("APP_ENVIRONMENT") == 'prod' else '/openapi.json',
)
app.mount("/static", StaticFiles(directory="app/api/static"), name="static")


# CORS
origins = [
    "http://localhost:8000",
    "https://ocada.ai",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "detail": ""
    }

app.include_router(r_characters.router)
app.include_router(r_instruments.router)
app.include_router(r_portfolios.router)
app.include_router(r_users.router)
app.include_router(r_skills.router)
app.include_router(r_social.router)
app.include_router(r_learn.router)
app.include_router(r_conversations.router)
