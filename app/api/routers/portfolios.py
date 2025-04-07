from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi import Query, Path, Body
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import app.api.constants as c
from app.models import api_schema, models
from app.api.dependencies import manager, SessionLocal, get_db
from app.api import crud
from app.api.exceptions import SnipsError
from app.api.tools.premium import validate_premium

router = APIRouter()


def calculate_portfolio_stats(db: Session, portfolio_id: int):
    crud.refresh_portfolio_stats(db=db, portfolio_id=portfolio_id,
                                 refresh_timeout=c.PORTFOLIO_STATS_UPDATE_TIMEOUT_SECONDS)


@router.post("/portfolios", response_model=api_schema.PortfolioView, tags=["portfolios"])
def create_portfolio(
    db: Session = Depends(get_db),
    portfolio: api_schema.PortfolioCreate = Body(
        ..., title="The portfolio to create"),
    user=Depends(manager),
):
    """
    Create a new portfolio
    """

    portfolio_count = crud.count_user_portfolios(db=db, user_id=user.id)
    if portfolio_count >= c.MAX_PORTFOLIOS_FREE_PLAN:
        raise HTTPException(
            status_code=403, detail="Could not create a new portfolio, as this would go over your plan limit. Upgrade to premium")
    try:
        db_portfolio = crud.create_portfolio(
            db=db,
            user_id=user.id,
            status='active',
            cash_balance=1000.0,
            portfolio_req=portfolio
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=400, detail="Could not create a portfolio. The character likely does not exist")
    return db_portfolio


@router.get("/portfolios", response_model=List[api_schema.PortfolioView], tags=["portfolios"])
def get_portfolios(
    q: Optional[str] = Query(
        None,
        title="Search query",
        description="Search for a portfolio by name",
        max_length=50),
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    target_user_id: Optional[int] = Query(
        None,
        title="The user ID to filter portfolios by",
        ge=1,
    ),
    user=Depends(manager)
):
    """
    Get all portfolios
    """
    q_clean = q if q is None else q.strip()
    db_portfolios = crud.get_portfolios_by_user_id(
        db=db, q=q_clean,
        target_user_id=target_user_id if target_user_id is not None else user.id,
        requester_user_id=user.id,
        skip=skip, limit=limit)
    return db_portfolios

# todo: deprecate in summer 2023
@router.get("/portfolios/leaderboard", response_model=List[api_schema.PortfolioView], tags=["portfolios"])
def get_portfolios_leaderboard(
    q: Optional[str] = Query(
        None,
        title="Search query",
        description="Search for a portfolio by name",
        max_length=50),
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get portfolios list sorted by gain
    """
    q_clean = q if q is None else q.strip()
    db_portfolios = crud.get_portfolios_leaderboard(
        db=db, q=q_clean,
        skip=skip, limit=limit)
    return db_portfolios


@router.get("/portfolios/{portfolio_id}", response_model=api_schema.PortfolioUserView, tags=["portfolios"])
def get_portfolio(
    background_tasks: BackgroundTasks,
    portfolio_id: int = Path(...,
                             title="The portfolio unique identifier", ge=1),
    db: Session = Depends(get_db),
    user=Depends(manager),
):
    """
    Get portfolio by ID
    """
    db_portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    elif db_portfolio.user_id != user.id and db_portfolio.is_public == 0:
        raise HTTPException(status_code=403, detail="Not authorized")
    background_tasks.add_task(calculate_portfolio_stats, db, portfolio_id)
    return db_portfolio


@router.patch("/portfolios/{portfolio_id}/character/is_public", response_model=api_schema.PortfolioView, tags=["portfolios"])
def set_portfolio_public_or_private(
    portfolio_id: int = Path(...,
                             title="The portfolio unique identifier", ge=1),
    is_public: bool = Body(
        ...,
        title="Set the portfolio public (true) or private (false)",
        embed=True
    ),
    db: Session = Depends(get_db),
    user=Depends(manager),

):
    """
    Set portfolio public/private by ID
    """
    db_portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    elif db_portfolio.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        db_portfolio = crud.set_portfolio_public(db=db, portfolio_id=portfolio_id, is_public=is_public)
    except Exception:
        raise HTTPException(status_code=500, detail="We could not set portfolio public/private")

    return db_portfolio


@router.patch("/portfolios/{portfolio_id}/character/name", response_model=api_schema.PortfolioView, tags=["portfolios"])
def set_portfolio_name(
    portfolio_id: int = Path(...,
                             title="The portfolio unique identifier", ge=1),
    name: str = Body(
        ...,
        title="New character name",
        embed=True,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager),

):
    """
    Set new portfolio name by ID
    """
    db_portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    elif db_portfolio.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        db_portfolio = crud.set_portfolio_name(db=db, portfolio_id=portfolio_id, name=name)
    except Exception:
        raise HTTPException(status_code=500, detail="We could not set portfolio name")

    return db_portfolio


@router.patch("/portfolios/{portfolio_id}/character/character_id", response_model=api_schema.PortfolioView, tags=["portfolios"])
def set_portfolio_new_character(
    portfolio_id: int = Path(...,
                             title="The portfolio unique identifier", ge=1),
    character_id: str = Body(
        ...,
        title="New character ID",
        embed=True,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager),

):
    """
    Set new portfolio avatar by ID
    """
    db_portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    elif db_portfolio.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        db_portfolio = crud.set_portfolio_character_id(db=db, portfolio_id=portfolio_id, character_id=character_id)
    except Exception:
        raise HTTPException(status_code=500, detail="We could not set new character avatar")

    return db_portfolio


@router.delete("/portfolios/{portfolio_id}", response_model=api_schema.PortfolioView, tags=["portfolios"])
def delete_portfolio(
    portfolio_id: int = Path(...,
                             title="The portfolio unique identifier", ge=1),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Delete portfolio by ID
    """
    db_portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    elif db_portfolio.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="You do not own this portfolio")
    db_portfolio = crud.mark_portfolio_as_deleted(db=db, id=portfolio_id)
    return db_portfolio


@router.get("/portfolios/{portfolio_id}/holdings", response_model=List[api_schema.Holding], tags=["portfolios"])
def get_portfolio_holdings(
    background_tasks: BackgroundTasks,
    portfolio_id: int = Path(...,
                             title="The portfolio unique identifier", ge=1),
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    sort_by: str = Query(
        "date_last_updated",
        title="The field to sort by",
        description="The field to sort by",
    ),
    sort_order: str = Query(
        "desc",
        title="The sort order",
        description="The sort order",
    ),
    ignore_sold_off: bool = Query(
        True,
        title="Ignore sold-off holdings",
        description="Ignore holdings where the quantity is zero",
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get portfolio holdings by ID
    """
    db_portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    elif db_portfolio.user_id != user.id and db_portfolio.is_public == 0:
        raise HTTPException(status_code=403, detail="Not authorized")
    db_holdings = crud.get_holdings_by_portfolio_id(
        db=db, portfolio_id=portfolio_id, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, ignore_sold_off=ignore_sold_off)
    background_tasks.add_task(calculate_portfolio_stats, db, portfolio_id)
    return db_holdings


@router.get("/portfolios/{portfolio_id}/holdings/{instrument_id}", response_model=Optional[api_schema.Holding], tags=["portfolios"])
def get_portfolio_holding(
    portfolio_id: int = Path(...,
                             title="The portfolio unique identifier", ge=1),
    instrument_id: int = Path(...,
                              title="The instrument unique identifier", ge=1),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get a holding by portfolio ID and instrument ID
    """
    db_portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    elif db_portfolio.user_id != user.id and db_portfolio.is_public == 0:
        raise HTTPException(status_code=403, detail="Not authorized")
    db_holding = crud.get_holding_by_id(
        db=db, portfolio_id=portfolio_id, instrument_id=instrument_id)
    # if db_holding is None:
    #     raise HTTPException(status_code=404, detail="Holding not found")
    return db_holding


@router.get("/portfolios/{portfolio_id}/transactions", response_model=List[api_schema.PortfolioTransaction], tags=["portfolios"])
def get_portfolio_transactions(
    portfolio_id: int = Path(...,
                             title="The portfolio unique identifier", ge=1),
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get portfolio transactions by ID
    """
    db_portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    elif db_portfolio.user_id != user.id and db_portfolio.is_public == 0:
        raise HTTPException(status_code=403, detail="Not authorized")

    db_transactions = crud.get_transactions_by_portfolio_id(
        db=db, portfolio_id=portfolio_id, skip=skip, limit=limit)
    return db_transactions


@router.post("/portfolios/{portfolio_id}/transactions", response_model=api_schema.PortfolioTransaction, tags=["portfolios"])
def create_portfolio_transaction(
    portfolio_id: int = Path(...,
                             title="The portfolio unique identifier", ge=1),
    instrument_id: int = Body(...,
                              title="The instrument unique identifier", ge=1),
    transaction_type: models.PortfolioTransactionTypeUserScope = Body(
        ..., title="The transaction type",),
    quantity: float = Body(...,
                           title="The quantity of the instrument or sell", ge=0.0001),
    message: str = Body(None,
                        title="User-generated message/comment associated with the transaction"),
    db: Session = Depends(get_db),
    user=Depends(manager),
):
    """
    Create a new transaction and make it pending execution
    """
    portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    elif portfolio.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="You do not own this portfolio")

    instrument = crud.get_instrument_by_id(db=db, id=instrument_id)
    if instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    elif instrument.kpi_latest_price is None:
        raise HTTPException(
            status_code=403, detail="Instrument has no price data")

    try:
        transaction = crud.create_transaction(
            db=db,
            portfolio_id=portfolio_id,
            associated_instrument_id=instrument_id,
            transaction_type=transaction_type.value,  # unpack enum
            quantity=quantity,
            message=message,
        )
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(
            status_code=400, detail="Could not create a transaction")
    return transaction


@router.get("/transactions/{portfolio_transaction_id}", response_model=api_schema.PortfolioTransaction, tags=["portfolios"])
def get_portfolio_transaction(
    portfolio_transaction_id: int = Path(
        ..., title="The portfolio transaction unique identifier", ge=1),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get portfolio transaction by ID
    """
    db_portfolio_transaction = crud.get_portfolio_transaction_by_id(
        db=db, id=portfolio_transaction_id)
    if db_portfolio_transaction is None:
        raise HTTPException(
            status_code=404, detail="Portfolio transaction not found")
    elif db_portfolio_transaction.portfolio.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="You do not own this portfolio")
    return db_portfolio_transaction


@router.post("/transactions/{portfolio_transaction_id}", response_model=api_schema.PortfolioTransaction, tags=["portfolios"])
def execute_portfolio_transaction(
    portfolio_transaction_id: int = Path(
        ..., title="The portfolio transaction unique identifier", ge=1),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Execute a pending transaction
    """
    db_portfolio_transaction = crud.get_portfolio_transaction_by_id(
        db=db, id=portfolio_transaction_id)
    allowed_transaction_types = [
        item.value for item in models.PortfolioTransactionTypeUserScope]
    if db_portfolio_transaction is None:
        raise HTTPException(
            status_code=404, detail="Portfolio transaction not found")
    elif db_portfolio_transaction.portfolio.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="You do not own this portfolio")
    elif db_portfolio_transaction.transaction_type not in allowed_transaction_types:
        raise HTTPException(status_code=403, detail="You can only execute transactions of type {}".format(
            allowed_transaction_types))
    elif db_portfolio_transaction.status != 'pending':
        raise HTTPException(
            status_code=403, detail="Only pending transactions can be executed")
    elif db_portfolio_transaction.quantity <= 0:
        raise HTTPException(
            status_code=403, detail="Quantity must be greater than zero")
    elif db_portfolio_transaction.instrument.kpi_latest_price is None:
        raise HTTPException(
            status_code=403, detail="Instrument has no price data")
    elif db_portfolio_transaction.instrument.kpi_latest_price.price <= 0:
        raise HTTPException(
            status_code=403, detail="Instrument price must be greater than zero")

    try:
        portfolio_transaction = crud.execute_portfolio_transaction(
            db=db,
            id=portfolio_transaction_id,
        )
    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(
            status_code=400, detail="Could not execute the transaction due to a database error")
    except SnipsError as e:
        print(e)
        raise HTTPException(
            status_code=400, detail="Could not execute the transaction due to a Snips error")

    if portfolio_transaction.transaction_type == models.PortfolioTransactionTypeUserScope.BUY.value:
        crud.credit_xp_on_buy_if_eligible(
            db=db,
            transaction_id=portfolio_transaction.id
        )
    elif portfolio_transaction.transaction_type == models.PortfolioTransactionTypeUserScope.SELL.value:
        crud.credit_xp_on_sell_if_eligible(
            db=db,
            transaction_id=portfolio_transaction.id
        )
    crud.credit_xp_on_transaction_execute_if_eligible(db=db, transaction_id=portfolio_transaction.id)
    
    return portfolio_transaction

@router.get("/transactions", response_model=List[api_schema.PortfolioTransactionDetailed], tags=["portfolios"])
def get_transactions(
    skip: int = 0,
    limit: int = Query(
        c.MAX_ELEMENTS_PER_PAGE,
        le=c.MAX_ELEMENTS_PER_PAGE,
    ),
    filter: str = Query(
        'EXECUTED_TRADES',
        title='Filter transactions, default only executed trades'
    ),
    sort: str = Query(
        'DESC',
        title='Sorting by date_executed'
    ),
    db: Session = Depends(get_db),
    user=Depends(manager)
):
    """
    Get all transactions
    """

    db_transactions = crud.get_transactions(
        db=db, skip=skip, limit=limit,
        filter=filter, sort=sort
        )
    return db_transactions



@router.post(
    "/portfolios/{portfolio_id}/claims/all",
    response_model=api_schema.RewardClaimResponse,
    tags=["portfolios"])
def claim_all_rewards(
    db: Session = Depends(get_db),
    portfolio_id: int = Path(...,
         title="The portfolio unique identifier", ge=1),
    revcat_public_api_key: str = Body(
        None,
        title="RevenueCat API key",
        description="If set, triggers validation of Premium membership",
        embed=True
    ),

    user=Depends(manager),
):
    is_premium = False
    portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if portfolio is None:
        raise HTTPException(
            status_code=404, detail="Portfolio not found")
    elif portfolio.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="You are not authorised to claim on behalf of this portfolio/character")
    
    datetime_now = datetime.now(tz=timezone.utc)

    delta_intraday_reward = timedelta(hours=1, minutes=55)  # 1h45m instead of 2 hours to account for UX
    delta_daily_reward = timedelta(hours=18)  # 18 hours instead of 24 to account for UX
    delta_weekly_reward = timedelta(hours=160)  # 160 hours instead of 168 to account for UX

    reward_schedule = {
        'REWARD_WEEKLY': {
            'FREE_PLAN': c.REWARD_WEEKLY_FREE_PLAN,
            'PREMIUM_PLAN': c.REWARD_WEEKLY_PREMIUM_PLAN,
            'is_eligible': portfolio.date_last_claimed_weekly_reward is None or portfolio.date_last_claimed_weekly_reward <= (datetime_now - delta_weekly_reward)
        },
        'REWARD_DAILY': {
            'FREE_PLAN': c.REWARD_DAILY_FREE_PLAN,
            'PREMIUM_PLAN': c.REWARD_DAILY_PREMIUM_PLAN,
            'is_eligible': portfolio.date_last_claimed_daily_reward is None or portfolio.date_last_claimed_daily_reward <= (datetime_now - delta_daily_reward)

        },
        'REWARD_INTRADAY': {
            'FREE_PLAN': c.REWARD_INTRADAY_FREE_PLAN,
            'PREMIUM_PLAN': c.REWARD_INTRADAY_PREMIUM_PLAN,
            'is_eligible': portfolio.date_last_claimed_intraday_reward is None or portfolio.date_last_claimed_intraday_reward <= (datetime_now - delta_intraday_reward)
        }
    }

    if revcat_public_api_key is not None:
        is_premium = validate_premium(
            user_id=user.id,
            secret_id=user.secret_id,
            revcat_public_api_key=revcat_public_api_key,
            should_update_user=True
        )

    plan_type = 'PREMIUM_PLAN' if is_premium else 'FREE_PLAN'
    total_claimed = 0
    xp_earned = 0

    for reward_type, reward_item in reward_schedule.items():
        if reward_item['is_eligible']:
            reward_amount = reward_item.get(plan_type, 0)
            try:
                crud.claim_portfolio_reward(
                    db=db, portfolio_id=portfolio_id, reward_type=reward_type, reward_amount=reward_amount
                )
                total_claimed = total_claimed + reward_amount
            except SnipsError as e:
                raise HTTPException(
                    status_code=400, detail="Could not claim a bonus")

            # credit XP for claiming a bonus
            try:
                crud.credit_xp_by_user_id(
                    db=db,
                    user_id=portfolio.user_id,
                    xp_amount=c.XP_CREDIT.COLLECT_REWARD,
                    xp_reason=c.XP_REASON.COLLECT_REWARD,
                    xp_detail=reward_type
                )
                xp_earned = xp_earned + c.XP_CREDIT.COLLECT_REWARD
            except Exception as e:
                db.rollback()

    crud.refresh_portfolio_stats(db=db, portfolio_id=portfolio_id, refresh_timeout=0)
    # portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    return {
        'total_claimed': total_claimed,
        'xp_earned': xp_earned
    }
  

@router.post(
    "/portfolios/{portfolio_id}/claims/{claim_type}",
    response_model=api_schema.PortfolioView,
    tags=["portfolios"])
def claim_bonus(
    db: Session = Depends(get_db),
    portfolio_id: int = Path(...,
         title="The portfolio unique identifier", ge=1),
    claim_type: str = Path(
        ...,
        title='REWARD_WEEKLY or REWARD_DAILY'
    ),
    revcat_public_api_key: str = Body(
        None,
        title="RevenueCat API key",
        description="If set, triggers validation of Premium membership",
        embed=True
    ),

    user=Depends(manager),
):
    """
    Claim a bonus
    """

    is_premium = False
    portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
    if claim_type not in ['REWARD_DAILY', 'REWARD_WEEKLY']:
        raise HTTPException(
            status_code=400, detail="claim_type invalid")
    elif portfolio is None:
        raise HTTPException(
            status_code=404, detail="Portfolio not found")
    elif portfolio.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="You are not authorised to claim on behalf of this portfolio/character")


    datetime_now = datetime.now(tz=timezone.utc)
    delta_daily_reward = timedelta(hours=18)  # 18 hours instead of 24 to account for UX
    delta_weekly_reward = timedelta(hours=160)  # 160 hours instead of 168 to account for UX
    
    reward_schedule = {
        'REWARD_WEEKLY': {
            'FREE_PLAN': c.REWARD_WEEKLY_FREE_PLAN,
            'PREMIUM_PLAN': c.REWARD_WEEKLY_PREMIUM_PLAN
        },
        'REWARD_DAILY': {
            'FREE_PLAN': c.REWARD_DAILY_FREE_PLAN,
            'PREMIUM_PLAN': c.REWARD_DAILY_PREMIUM_PLAN
        }
    }

    is_eligible_for_weekly_reward = claim_type == 'REWARD_WEEKLY' and \
        (portfolio.date_last_claimed_weekly_reward is None or portfolio.date_last_claimed_weekly_reward <= (datetime_now - delta_weekly_reward))
    is_eligible_for_daily_reward = claim_type == 'REWARD_DAILY' and \
        (portfolio.date_last_claimed_daily_reward is None or portfolio.date_last_claimed_daily_reward <= (datetime_now - delta_daily_reward))

    if revcat_public_api_key is not None:
        is_premium = validate_premium(
            user_id=user.id,
            secret_id=user.secret_id,
            revcat_public_api_key=revcat_public_api_key,
            should_update_user=True
        )

    if is_eligible_for_weekly_reward or is_eligible_for_daily_reward:
        plan_type = 'PREMIUM_PLAN' if is_premium else 'FREE_PLAN'
        reward_amount = reward_schedule.get(claim_type, {}).get(plan_type, 0)
        try:
            crud.claim_portfolio_reward(
                db=db, portfolio_id=portfolio_id, reward_type=claim_type, reward_amount=reward_amount
            )
        except SnipsError as e:
            raise HTTPException(
                status_code=400, detail="Could not claim a bonus")

        # credit XP for claiming a bonus
        try:
            crud.credit_xp_by_user_id(
                db=db,
                user_id=portfolio.user_id,
                xp_amount=c.XP_CREDIT.COLLECT_REWARD,
                xp_reason=c.XP_REASON.COLLECT_REWARD,
                xp_detail=claim_type
            )
        except Exception as e:
            db.rollback()

        crud.refresh_portfolio_stats(db=db, portfolio_id=portfolio_id, refresh_timeout=0)
        portfolio = crud.get_portfolio_by_id(db=db, id=portfolio_id)
        return portfolio

    else:
        raise HTTPException(
            status_code=403, detail="You can't claim a reward at this time, please wait")

