from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query, Path, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

import os
import json

import openai
from datetime import datetime

import app.api.constants as c
from app.models import api_schema, enums
from app.api.dependencies import manager, get_db
from app.api import crud
from app.api.tools.premium import validate_premium
from app.api.firebase_custom_client import client_instance as fcc
from app.api.tools.utils import encoded_var_to_creds

from app.api.tools.ai_agent import AIAgent

router = APIRouter()

# required to use text-bison
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = encoded_var_to_creds('BISON_CREDS')
# required to use open ai
openai.api_key = os.getenv('OPEN_AI_KEY')

@router.get(
    "/conversations",
    # TODO: add the schema back once it's created in Models
    # response_model=List[api_schema.Conversation],
    tags=["conversations"])
def list_user_conversations(
    user=Depends(manager)
):
    conversation_list = fcc.get_conversations_by_user_id(user.id)
    return conversation_list


@router.post(
    "/conversations/{conversation_id}/seen",
    # TODO: add the schema back once it's created in Models
    # response_model=api_schema.Conversation,
    tags=["conversations"]
)
def mark_seen(
    conversation_id: str = Path(
        ...,  # mandatory field, no default value
        title="Conversation ID",
        description="UUID generated on a client device",
        max_length=36  # UUIDs are 36 characters long, incl. dashes
    ),
    user=Depends(manager)
):
    try:
        fcc.conversation_seen(conversation_id, user.id)
        return {
            "success": True,
        }
    except Exception as e:
        print(f'[user_{user.id}] ERROR: Failed to mark conversation as seen. Reason:', e)
        return {
            "success": False,
        }


@router.post(
    "/conversations/{conversation_id}",
    # TODO: add the schema back once it's created in Models
    # response_model=api_schema.Conversation,
    tags=["conversations"]
)
def send_message(
    conversation_id: str = Path(
        ...,  # mandatory field, no default value
        title="Conversation ID",
        description="UUID generated on a client device",
        max_length=36  # UUIDs are 36 characters long, incl. dashes
    ),
    message: str = Body(
        ...,  # mandatory field, no default value
        title="Message",
        description="Prompt sent to the AI",
        max_length=100,
        embed=True,
    ),
    revcat_public_api_key: str = Body(
        None,
        title="RevenueCat API key",
        description="If set, triggers validation of Premium membership",
        embed=True
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    # this takes quite a while, so let's track the time
    start_time = datetime.now()
    user = crud.get_user_by_id(db=db, id=user.id)

    print(f'[user_{user.id}] received a new message from user at {conversation_id}')

    if (conversation_id in ['announcements', 'news']):
        print(f'[user_{user.id}] tried to send a message to {conversation_id}: {message}')
        doc = fcc.save_message(message, conversation_id, user_id=user.id, sender=user.id)
        fcc.save_to_feed('feedback', doc)
        return {
            "response": "Alright 😀",
            "credits_remaining": user.credit_balance,
            "send_message_fee": 0
        }

    message_doc = fcc.save_message(message, conversation_id, user_id=user.id, sender=user.id)
    if conversation_id in ['feedback']:
        fcc.save_to_feed('feedback', message_doc)
        response = 'Thank you for the feedback 🙏 We will get back to you ASAP 🙂'
        fcc.save_message(response, conversation_id, user_id=user.id, sender='system')
        return {
            "response": response,
            "credits_remaining": user.credit_balance,
            "send_message_fee": 0
        }
    else:
        fcc.save_to_feed('message_feed', message_doc)

    if not user.portfolios:
        response = 'You must set up your profile before using AI. Please complete your onboarding first.'
        fcc.save_message(response, conversation_id, user_id=user.id, sender='system')
        return {
            "response": response,
            "credits_remaining": user.credit_balance,
            "send_message_fee": c.AI_CREDIT.SEND_MESSAGE_FEE
        }

    if not fcc.lock_user(user.id):
        response = "Whoa there, Speedy Gonzales! Slow down a bit, and I'll do my best to keep up 😄 Ask only one question at a time."
        fcc.save_message(response, conversation_id, user_id=user.id, sender='system')
        return {
            "response": response,
            "credits_remaining": user.credit_balance,
            "send_message_fee": c.AI_CREDIT.SEND_MESSAGE_FEE
        }

    # validate premium
    # adds bonus credits if the user upgrades
    # purchase transfer could be exploited though:
    # https://www.revenuecat.com/docs/restoring-purchases#transferring-purchases-seen-on-multiple-app-user-ids
    if revcat_public_api_key is not None:
        validate_premium(
            user_id=user.id,
            secret_id=user.secret_id,
            revcat_public_api_key=revcat_public_api_key,
            should_update_user=True
        )
        db.refresh(user)

    # verify if the user has sufficient credit balance
    if user.credit_balance < c.AI_CREDIT.SEND_MESSAGE_FEE:
        response = "Thank you for trying Snips AI 😌 You have reached the message limit. Upgrade to Premium to get more 🔥"
        fcc.save_message(response, conversation_id, user_id=user.id, sender='system')
        return {
            "response": response,
            "credits_remaining": user.credit_balance,
            "send_message_fee": c.AI_CREDIT.SEND_MESSAGE_FEE
        }

    # Anything that might be useful to know about the user
    user_meta_data = {
        # 'portfolio': 'Holding 25 TSLA stocks since 1st of Sep 2022 and 1 ETH from 8th of Apr 2022',
        # 'goal': 'Make 1 mil USD by 2025',
        # 'risk_tolerance': 'Risk taker',
        # 'market_knowledge': 'low'
    }

    # Get top 5 largest positions from users' portfolio
    user_portfolio = []
    for holding in user.portfolios[0].holdings:
        # skip closed postions
        if (holding.quantity == 0): continue
        holding = {
            'name': holding.instrument.name,
            'symbol': holding.instrument.symbol,
            'quantity': round(holding.quantity, 2),
            'avg_purchase_price': round(holding.average_price, 2),
            'current_price': round(holding.instrument.kpi_latest_price.price, 2),
            'P&L': round(holding.quantity*holding.instrument.kpi_latest_price.price - holding.quantity*holding.average_price, 2),
            'internal_id': holding.instrument.id
        }
        user_portfolio.append(holding)

    sorted_portfolio = sorted(user_portfolio, key=lambda x: x['quantity'] * x['current_price'], reverse=True)

    user_meta_data['virtual_portfolio'] = sorted_portfolio[0:30] if sorted_portfolio else 'no positions yet'
    target_net_worth = crud.get_user_long_term_goal(db=db, user_id=user.id)
    goal = f'Make {target_net_worth} in 5 years' if target_net_worth else None
    if goal:
        user_meta_data['goal'] = goal

    # user_meta_data['risk_tolerance'] = 'is a BIG risk taker' if user.portfolios[0].is_risk_taker else 'not a big risk taker'
    # user_meta_data['usd_balance'] = round(user.portfolios[0].cash_balance, 2)
    user_meta_data['virtual_balance_usd'] = user.portfolios[0].cash_balance
    
    solana_accounts = [account.ext_user_id for account in user.accounts if account.provider == 'solana']
    solana_wallet_addr = solana_accounts[0] if solana_accounts else None
    user_meta_data['live_solana_wallet_address'] = solana_wallet_addr if solana_wallet_addr else 'not set yet, user should connect it in settings'
    
    print(f'[user_{user.id}] collected user metadata: {user_meta_data}')

    # Get messages history if any (NOTE: have to do this after setting a new message)
    history = []
    sorted_messages = fcc.get_messages_by_conversation_id(
        user_id=user.id,
        conversation_id=conversation_id,
        skip=0,
        limit=5,
        reverse=True)['messages']
    for msg in sorted_messages:
        # OpenAI expects either system or user senders
        if (msg['sender'] == 'system'):
            history.append({'role': 'system', 'content': msg['content']})
        else:
            history.append({'role': 'user', 'content': msg['content']})


    print(f'[user_{user.id}] prepared messages history: {history}')

    ai_response = None
    ai_retries = 3
    ai_agent = AIAgent(db_session=db, recent_messages=history, user_meta_data=user_meta_data, portfolio_id=user.portfolios[0].id)
    while ai_retries > 0:
        try:
            ai_response = ai_agent.process_message(user.id, message)
            # ai_response = get_response_from_ai(user.id, history, user_meta_data)
            break
        except Exception as e:
            print(f'[user_{user.id}] ERROR: get_response_from_ai failed. Retrying... Reason:', e)
            ai_retries -= 1

    if not ai_response:
        print(f'[user_{user.id}] ERROR: get_response_from_ai() failed')
        fcc.release_user(user.id)
        raise HTTPException(status_code=500, detail="Failed to generate a response")

    # charge the user
    crud.reduce_credits_by_user_id(
        db=db,
        user_id=user.id,
        credit_amount=c.AI_CREDIT.SEND_MESSAGE_FEE,
    )
    crud.credit_xp_by_user_id(
        db=db,
        user_id=user.id,
        xp_amount=c.XP_CREDIT.AI_MESSAGE,
        xp_reason=c.XP_REASON.AI_MESSAGE,
        xp_detail=f"ID={conversation_id}",
    )

    doc = fcc.save_message(ai_response.replace('**', '').replace('* ', '- ').replace('###', '#'), conversation_id, user_id=user.id, sender='system')
    fcc.save_to_feed('message_feed', doc)
    fcc.release_user(user.id)
    
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    print(f'[user_{user.id}] took {elapsed_time.seconds} seconds to generate a response')
    del ai_agent

    return {
        "response": ai_response.replace('**', '').replace('* ', '- ').replace('###', '#'),
        "credits_remaining": user.credit_balance,
        "send_message_fee": c.AI_CREDIT.SEND_MESSAGE_FEE 
    }


@router.get(
    "/conversations/{conversation_id}",
    # TODO: add the schema back once it's created in Models
    # response_model=api_schema.Conversation,
    tags=["conversations"]
)
def get_user_conversation(
    conversation_id: str = Path(
        ...,  # mandatory field, no default value
        title="Conversation ID",
        description="UUID generated on a client device",
        max_length=36  # UUIDs are 36 characters long, incl. dashes
    ),
    instrument_id: int = Query (
        None,
        title='Token ID',
        description='Token/instrument associated with this conversation: influences suggested prompts etc.'
    ),
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    instrument = crud.get_instrument_by_id(db=db, id=instrument_id) if instrument_id else None

    suggested_prompts = \
    [ # suggested prompts for conversation triggered from the token screen
        f'Analyze price action for ${instrument.symbol}',
        f'Analyze socials for ${instrument.symbol}',
    ] \
    if instrument else \
    [ # prompts for a generic conversation
        'How is the market performing today?',
        'Analyze my virtual portfolio',
        'Analyze my live Solana wallet PnL',
        'What should I consider buying next?',
        'How can I reach my goal?',
        'What are the major market trends recently?'
    ]
    resp = fcc.get_messages_by_conversation_id(
        user_id=user.id,
        conversation_id=conversation_id,
        skip=skip,
        limit=limit,
        reverse=True
        )
    return {
        'messages': resp['messages'],
        'display_name': resp['display_name'],
        'last_update': resp['last_update'],
        'unseen': resp['unseen'],
        'show_prompts': resp['show_prompts'],
        'suggested_prompts': suggested_prompts,
        'allow_input': resp['allow_input'],
        'credits_remaining': user.credit_balance,
        'send_message_fee': 0 if conversation_id in ['news', 'feedback', 'announcements'] else c.AI_CREDIT.SEND_MESSAGE_FEE 
    }

@router.get(
    "/conversations_stats",
    tags=["conversations"])
def get_conversations_stats(
    user=Depends(manager)
):
    unseen_count = fcc.get_unseen_conversation_count_by_user_id(user.id)
    return {
        'unseen': unseen_count
    }