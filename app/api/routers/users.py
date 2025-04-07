
from datetime import timedelta
import datetime
import json
from typing import List, Optional
from enum import Enum
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query, Path, Body
import nacl.exceptions
import nacl.signing
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
import jwt
import base58
import nacl

import app.api.constants as c
from app.models import api_schema, models
from app.api.dependencies import manager, SessionLocal, get_db
from app.api import crud
from app.api.exceptions import SnipsError
from app.api.auth.apple_auth import AppleAuth
from app.api.auth.google_auth import GoogleAuth
from app.api.tools.premium import validate_premium
from app.api.firebase_custom_client import client_instance as fcc

router = APIRouter()

apple_auth = AppleAuth()
google_auth = GoogleAuth()

class AuthProvider(str, Enum):
    apple = "apple"
    google = "google"
    solana = "solana"

class CommitmentLevel(str, Enum):
    casual = "casual"
    serious = "serious"

class PushTokenProviderEnum(str, Enum):
    EXPO = 'EXPO'  # expo notifications
    #APNS = 'APNS'  # apple push notifications service
    #FCM = 'FCM'  # firebase cloud messaging

@manager.user_loader()
def get_user(
        user_id: str,
        db: Session = Depends(get_db)):
    db = SessionLocal()
    try:
        user = crud.get_user_by_id(db=db, id=user_id)
        if user:
            # return user
            return crud.update_user_last_active_date(db=db, user_id=user_id)
    finally:
        # pass
        db.close()


@router.post("/auth/solana",
            response_model=api_schema.LoggedInUser,
            tags=["users"])
def auth_with_public_key(
    public_key: str = Body(
        ...,
        title="Public key address (wallet)",
        description="Base58 encoded public key",
        embed=True
    ),
    signed_message: str = Body(
        ...,
        title="Signed message",
        description="Base58 encoded message the key owner signed",
        embed=True
    ),
    signature: str = Body(
        ...,
        title="Signature",
        description="Base58 encoded signature provided by the key owner",
        embed=True
    ),
    db: Session = Depends(get_db)
):
    db = SessionLocal()

    # convert base58 strings into binary
    public_key_bytes = base58.b58decode(public_key)
    signed_message_bytes = base58.b58decode(signed_message)
    signature_bytes = base58.b58decode(signature)
    provider = AuthProvider.solana.value

    # validate the key
    verify_key = nacl.signing.VerifyKey(public_key_bytes)
    try:
        is_valid_signature = verify_key.verify(signed_message_bytes, signature_bytes)
        print('is valid signature', is_valid_signature)
    except nacl.exceptions.BadSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    db_user = crud.get_user_by_ext_user_id(
        db=db, provider=provider, ext_user_id=public_key)

    if db_user is None:
        # create new user + link the account
        try:
            new_user = crud.create_user(
                db=db,
                user=models.User(
                    secret_id=uuid4().hex,
                    credit_balance=c.AI_CREDIT.NEW_USER_ADD
                    )
                )
            new_account = models.Account(
                provider=provider,
                user_id=new_user.id,
                ext_user_id=public_key,
                detail=''
            )
            db.merge(new_account)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=409, detail="Cannot create a new account")
        
        # credit XP on signing up
        try:
            crud.credit_xp_by_user_id(
                db=db,
                user_id=new_user.id,
                xp_amount=c.XP_CREDIT.SIGNUP,
                xp_reason=c.XP_REASON.SIGNUP
            )
        except Exception as e:
            db.rollback()

        access_token = manager.create_access_token(
            data={'sub': new_user.id},
            expires=timedelta(hours=c.VERIFIED_USER_TOKEN_EXPIRATION_HOURS)
        )

        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'user': new_user
        }

    access_token = manager.create_access_token(
        data={'sub': db_user.id},
        expires=timedelta(hours=c.VERIFIED_USER_TOKEN_EXPIRATION_HOURS)
    )

    return {
        'access_token': access_token,
        'token_type': 'Bearer',
        'user': db_user
    }

    

@router.post("/auth/{provider}", response_model=api_schema.LoggedInUser, tags=["users"])
def auth_with_ext_account(
    token: str = Body(
        ...,
        title="JWT or access token",
        description="JWT or access token",
        embed=True),
    db: Session = Depends(get_db),
    provider: AuthProvider = Path(..., title="External identity provider")
):
    """
    Authenticate with an external identity provider
    """
    db = SessionLocal()
    try:
        if provider == AuthProvider.google:
            ext_user = google_auth.validate_access_token(token)
        elif provider == AuthProvider.apple:
            ext_user = apple_auth.validate_jwt(token)
    except jwt.exceptions.PyJWTError as e:
        raise HTTPException(status_code=400, detail="Invalid identity token")

    db_user = crud.get_user_by_ext_user_id(
        db=db, provider=provider, ext_user_id=ext_user.user_id)

    if db_user is None:
        # create new user + link the account
        try:
            new_user = crud.create_user(
                db=db,
                user=models.User(
                    email=ext_user.email,
                    secret_id=uuid4().hex,
                    credit_balance=c.AI_CREDIT.NEW_USER_ADD
                    )
                )
            new_account = models.Account(
                provider=provider,
                user_id=new_user.id,
                ext_user_id=ext_user.user_id,
                detail=json.dumps(ext_user.raw)
            )
            db.merge(new_account)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=409, detail="Cannot create a new account")
        
        # credit XP on signing up
        try:
            crud.credit_xp_by_user_id(
                db=db,
                user_id=new_user.id,
                xp_amount=c.XP_CREDIT.SIGNUP,
                xp_reason=c.XP_REASON.SIGNUP
            )
        except Exception as e:
            db.rollback()

        access_token = manager.create_access_token(
            data={'sub': new_user.id},
            expires=timedelta(hours=c.VERIFIED_USER_TOKEN_EXPIRATION_HOURS)
        )

        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'user': new_user
        }

    access_token = manager.create_access_token(
        data={'sub': db_user.id},
        expires=timedelta(hours=c.VERIFIED_USER_TOKEN_EXPIRATION_HOURS)
    )

    return {
        'access_token': access_token,
        'token_type': 'Bearer',
        'user': db_user
    }




@router.post("/users", response_model=api_schema.LoggedInUser, tags=["users"])
def create_anonymous_user(
    db: Session = Depends(get_db)
):
    db = SessionLocal()

    # create new user
    try:
        user = crud.create_user(
            db=db,
            user=models.User(
                secret_id=uuid4().hex,
                credit_balance=c.AI_CREDIT.NEW_USER_ADD
            ))
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot create a new account"
        )

    # credit XP on signing up
    try:
        crud.credit_xp_by_user_id(
            db=db,
            user_id=user.id,
            xp_amount=c.XP_CREDIT.SIGNUP,
            xp_reason=c.XP_REASON.SIGNUP
        )
    except Exception as e:
        db.rollback()

    access_token = manager.create_access_token(
        data={'sub': user.id},
        expires=timedelta(hours=c.ANONYMOUS_USER_TOKEN_EXPIRATION_HOURS)
    )

    fcc.init_user_conversations(user.id)

    return {
        'access_token': access_token,
        'token_type': 'Bearer',
        'user': user
    }


@router.get("/users/me", response_model=api_schema.CurrentUser, tags=["users"])
def get_current_user(
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    # db = SessionLocal()
    db_user = crud.get_user_by_id(db=db, id=user.id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/users/me/experience", response_model=api_schema.CurrentUser, tags=["users"])
def set_investing_experience(
    db: Session = Depends(get_db),
    user=Depends(manager),
    has_experience: bool = Query(
        ...,
        title="The user's investing experience"
    )
):
    updated_user = crud.set_investing_experience(
        db=db, user_id=user.id, has_experience=has_experience)
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.put("/users/me/referrer", response_model=api_schema.CurrentUser, tags=["users"])
def set_referrer(
    db: Session = Depends(get_db),
    user=Depends(manager),
    referrer_id: int = Body(
        ...,
        title="The user's referrer",
        gt=0,
        embed=True
    )
):
    if user.referrer_id:
        raise HTTPException(status_code=400, detail="Referrer bonus has already been received")
    elif user.referrer_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot be your own referrer")
    else:
        updated_user = crud.set_referrer_if_empty(
            db=db, user_id=user.id, referrer_id=referrer_id)
        
        # credit XP if referrer was updated
        if updated_user.referrer_id:
            try:
                crud.credit_xp_by_user_id(
                    db=db,
                    user_id=user.id,
                    xp_amount=c.XP_CREDIT.REFEREE,
                    xp_reason=c.XP_REASON.REFEREE,
                    xp_detail=f"REFERRER={referrer_id}"
                )
            except Exception as e:
                db.rollback()

        else:
            raise HTTPException(status_code=400, detail="Referrer ID is invalid")

        if updated_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_user


@router.put("/users/me/long_term_goal", response_model=api_schema.CurrentUser, tags=["users"])
def set_long_term_goal(
    db: Session = Depends(get_db),
    user=Depends(manager),
    target_net_worth: int = Body(
        ...,
        title="The user's goal in USD",
        gt=0,
        embed=True
    )
):
    updated_user = crud.set_user_long_term_goal(
        db=db, user_id=user.id, target_net_worth=target_net_worth)
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.put("/users/me/dream", response_model=api_schema.CurrentUser, tags=["users"])
def set_dream(
    db: Session = Depends(get_db),
    user=Depends(manager),
    dream_statement: str = Body(
        ...,
        title="The user's dream statement",
        min_length=0,
        max_length=150,
        embed=True
    )
):
    updated_user = crud.set_user_dream_statement(
        db=db, user_id=user.id, dream_statement=dream_statement)
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.put("/users/me/age", response_model=api_schema.CurrentUser, tags=["users"])
def set_age(
    db: Session = Depends(get_db),
    user=Depends(manager),
    age: int = Body(
        ...,
        title="The user's age",
        ge=3,
        le=120,
        embed=True
    )
):
    
    # Get the current year and month
    current_date = datetime.date.today()
    current_year = current_date.year
    current_month = current_date.month

    # Calculate the estimated birth year based on the current month
    if current_month <= 6:
        estimated_birth_year = current_year - age - 1
    else:
        estimated_birth_year = current_year - age

    updated_user = crud.set_user_birth_year(
        db=db, user_id=user.id, birth_year_estimated=estimated_birth_year)
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.put("/users/me/commitment", response_model=api_schema.CurrentUser, tags=["users"])
def set_commitment(
    db: Session = Depends(get_db),
    user=Depends(manager),
    commitment_level: CommitmentLevel = Body(
        ...,
        title="The user's dream statement",
        embed=True
    )
):
    updated_user = crud.set_user_commitment_level(
        db=db, user_id=user.id, commitment_level=commitment_level)
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.delete("/users/me/accounts/{provider}", response_model=api_schema.ConnectedExternalUserAccount, tags=["users"])
def disconnect_ext_account(
    db: Session = Depends(get_db),
    user=Depends(manager),
    provider: AuthProvider = Path(..., title="External identity provider")
):
    """
    Disconnect an external account (Google, Apple, etc.)
    """
    db = SessionLocal()
    ext_account = crud.get_account_by_user_id(
        db=db, user_id=user.id, provider=provider)
    if ext_account is None:
        raise HTTPException(status_code=404, detail="Nothing to disconnect")
    db.delete(ext_account)
    db.commit()
    return {
        "provider": provider,
        "user_id": user.id,
        "ext_user_id": ext_account.ext_user_id,
        "detail": "This Apple ID has been removed"
    }


@router.post("/users/me/accounts/solana",
            response_model=api_schema.ConnectedExternalUserAccount,
            tags=["users"])
def connect_public_key(
    public_key: str = Body(
        ...,
        title="Public key address (wallet)",
        description="Base58 encoded public key",
        embed=True
    ),
    signed_message: str = Body(
        ...,
        title="Signed message",
        description="Base58 encoded message the key owner signed",
        embed=True
    ),
    signature: str = Body(
        ...,
        title="Signature",
        description="Base58 encoded signature provided by the key owner",
        embed=True
    ),
    db: Session = Depends(get_db),
    user=Depends(manager),
):
    db = SessionLocal()

    # convert base58 strings into binary
    public_key_bytes = base58.b58decode(public_key)
    signed_message_bytes = base58.b58decode(signed_message)
    signature_bytes = base58.b58decode(signature)
    provider = AuthProvider.solana.value

    # validate the key
    verify_key = nacl.signing.VerifyKey(public_key_bytes)
    try:
        is_valid_signature = verify_key.verify(signed_message_bytes, signature_bytes)
        print('is valid signature', is_valid_signature)
    except nacl.exceptions.BadSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # create the external account in DB
    try:
        new_account = models.Account(
            provider=provider,
            user_id=user.id,
            ext_user_id=public_key,
            detail=''
        )
        db.merge(new_account)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This account is already connected")
    
    return {
        "provider": provider,
        "user_id": user.id,
        "ext_user_id": public_key,
        "detail": "This external account can now be used to log in"
    }


@router.post("/users/me/accounts/{provider}", response_model=api_schema.ConnectedExternalUserAccount, tags=["users"])
def connect_ext_account(
    db: Session = Depends(get_db),
    user=Depends(manager),
    provider: AuthProvider = Path(..., title="External identity provider"),
    token: str = Body(
        ...,
        title="Google access token",
        description="Google access token",
        embed=True
    ),
):
    """
    Connect an external account (Google, Apple, etc.)
    """
    db = SessionLocal()

    ext_user = None
    try:
        if provider == AuthProvider.google:
            ext_user = google_auth.validate_access_token(token)
        elif provider == AuthProvider.apple:
            ext_user = apple_auth.validate_jwt(token)
    except SnipsError as e:
        raise HTTPException(
            status_code=400, detail='Could not validate the access token')

    # create the external account in DB
    try:
        new_account = models.Account(
            provider=provider,
            user_id=user.id,
            ext_user_id=ext_user.user_id,
            detail=json.dumps(ext_user.raw)
        )
        db.merge(new_account)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This account is already connected")

    # extract the email address and save it to the Users table
    try:
        if user.email is None:
            user.email = ext_user.email
            db.merge(user)
            db.commit()
    except IntegrityError as e:
        db.rollback()

    return {
        "provider": provider,
        "user_id": user.id,
        "ext_user_id": ext_user.user_id,
        "detail": "This external account can now be used to log in"
    }


@router.post("/users/me/refresh_token", response_model=api_schema.LoggedInUser, tags=["users"])
def refresh_token(
    db: Session = Depends(get_db),
    last_seen_platform: str = Body(
        None,
        title="Users last used device platform",
        max_length=50,
        embed=True
    ),
    last_seen_app_version: str = Body(
        None,
        title="Users last used used app version",
        max_length=50,
        embed=True
    ),
    user=Depends(manager)
):

    db = SessionLocal()
    db_user = crud.get_user_by_id(db=db, id=user.id)

    crud.set_user_last_seen_attributes(
        db=db,
        user_id=user.id,
        platform_name=last_seen_platform,
        app_version=last_seen_app_version
    )

    access_token = manager.create_access_token(
        data={'sub': db_user.id},
        expires=timedelta(hours=c.ANONYMOUS_USER_TOKEN_EXPIRATION_HOURS)
    )

    return {
        'access_token': access_token,
        'token_type': 'Bearer',
        'user': db_user
    }


@router.delete("/users/me", response_model=api_schema.DeletedUserConfirmation, tags=["users"])
def delete_user(
    db: Session = Depends(get_db),
    user=Depends(manager),
):
    """
    Delete the user account with all user data
    """

    db_user = crud.get_user_by_id(db=db, id=user.id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        db.delete(db_user)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Cannot delete the user")

    return {
        "user": db_user,
        "deleted": True,
        "detail": "Your account has been deleted"
    }

@router.post("/users/me/push_token/{provider}",
# response_model=api_schema.ConnectedExternalUserAccount,
tags=["users"])
def add_push_token(
    db: Session = Depends(get_db),
    user=Depends(manager),
    provider: PushTokenProviderEnum = Path(..., title="Push token provider"),
    token: str = Body(
        ...,
        title="JWT access token issued by an external provider",
        description="JWT access token issued by an external provider",
        embed=True
    ),
):
    """
    Register a push notification token and assign it to a user
    """
    try:
        push_token = crud.activate_push_token(
            db=db,
            provider=provider,
            token=token,
            user_id=user.id
        )
    except SnipsError as e:
        raise HTTPException(
            status_code=400, detail="This token can't be added")
    
    return {
        'detail': 'Token registered'
    }

@router.delete("/users/me/push_token/{provider}",
# response_model=api_schema.ConnectedExternalUserAccount,
tags=["users"])
def disable_push_token(
    db: Session = Depends(get_db),
    user=Depends(manager),
    provider: PushTokenProviderEnum = Path(..., title="Push token provider"),
    token: str = Body(
        ...,
        title="JWT access token issued by an external provider",
        description="JWT access token issued by an external provider",
        embed=True
    ),
):
    """
    Disable a push notification token
    """
    push_token = crud.get_push_token(
        db=db,
        provider=provider,
        token=token,
    )

    if push_token is None:
        raise HTTPException(status_code=404, detail="Nothing to disable")
    elif push_token.user_id != user.id:
        raise HTTPException(status_code=403, detail="Nothing to disable")

    try:
        push_token = crud.disable_push_token(
            db=db,
            provider=provider,
            token=token
        )
    except SnipsError:
        raise HTTPException(status_code=500, detail="An error occurred when disabling the push notification token")
    return {
        'detail': 'Token disabled'
    }


@router.get("/users/{user_id}", response_model=api_schema.User, tags=["users"])
def get_user(
    user_id: int = Path(..., title="The user unique identifier", ge=1),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    db_user = crud.get_user_by_id(db=db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user