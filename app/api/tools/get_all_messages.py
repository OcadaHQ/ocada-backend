from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query, Path, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

import firebase_admin
from firebase_admin import firestore, credentials
from google.cloud.firestore_v1.base_query import FieldFilter

import os
import json
import requests
import openai
from datetime import datetime
from bardapi import BardCookies
from vertexai.language_models import TextGenerationModel

import app.api.constants as c
from app.models import api_schema, enums
from app.api.dependencies import manager, SessionLocal, get_db
from app.api import crud
from app.api.tools.premium import validate_premium
from app.api.tools.utils import encoded_var_to_creds

router = APIRouter()


# Initialize Firebase Admin SDK (should only be used within a trusted backend)
# TODO: run this on startup
creds = credentials.Certificate(encoded_var_to_creds('FIREBASE_ADMIN_CREDS'))
firebase_admin.initialize_app(creds)

# Firestore client
db_firestore = firestore.client()
# required to use text-bison
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = encoded_var_to_creds('BISON_CREDS')
# required to use open ai
openai.api_key = os.getenv('OPEN_AI_KEY')


all_messages = []
all_messages_by_user = {}
users_ref = db_firestore.collection('conversations')
users = users_ref.get()
for user in users:
    user_conversations_ref = db_firestore.collection('conversations').document(user.id).collection('user_conversations')
    conversations = user_conversations_ref.stream()
    all_messages_by_user[user.id] = []
    for conversation in conversations:
        messages_query = conversation.reference.collection('messages')
        messages_docs = messages_query.stream()
        for message_doc in messages_docs:
            data = message_doc.to_dict()
            if data['sender'] == 'system': continue
            all_messages.append(data)
            all_messages_by_user[user.id].append(data)

sorted_messages = sorted(all_messages, key=lambda x: x['ts'])
counter = 0
for message in sorted_messages:
    if (message['sender'] in [40, 3620, 2, 16, 34, 4553, 1100]): continue
    counter += 1
    # print(f"Sender: {message['sender']}")
    print(f"{message['ts']} [{message['sender']}]: {message['content']}")

for x in all_messages_by_user:
    for message in all_messages_by_user[x]:
        if message['ts'] == 1694961206.848106: print(x, message)

for x in all_messages_by_user:
    print(f'{x}: {len(all_messages_by_user[x])}')