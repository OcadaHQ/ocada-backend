from datetime import datetime, timedelta, timezone
from typing import List, Optional
import math

from sqlalchemy import or_, and_, func
import sqlalchemy
from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import SQLAlchemyError

import app.api.constants as c
from app.models import models, api_schema, enums
from app.api.exceptions import SnipsInsuficientFundsError, SnipsInsufficientInstrumentQuantityError, SnipsError

def get_instruments(db: Session, q: Optional[str], sort: Optional[str], show_well_known_only: Optional[int], skip: int, limit: int):

    order_by_options = {
        'default': models.Instrument.name,
        'name_asc': models.Instrument.name, 
        'price_change_perc_asc': models.InstrumentKPI_LatestPrice.change_perc_1d.asc(),
        'price_change_perc_desc': models.InstrumentKPI_LatestPrice.change_perc_1d.desc(),
        'cmc_rank': models.Instrument.cmc_rank.asc().nulls_last(),  # Ascending order, nulls last
        'shuffle': func.random()
    }
    order_by_param = order_by_options.get(sort) if order_by_options.get(sort, None) is not None else order_by_options.get('default')
    last_acceptable_price_update_date = datetime.now(timezone.utc) - timedelta(days=1)

    return db.query(models.Instrument) \
        .join(models.InstrumentKPI_LatestPrice, models.InstrumentKPI_LatestPrice.instrument_id == models.Instrument.id) \
        .filter(
            or_(
                models.Instrument.symbol.ilike(f"%{q}%"),
                models.Instrument.name.ilike(f"%{q}%"),
                models.Instrument.subtitle.ilike(f"%{q}%"),
                models.Instrument.tags.ilike(f"%{q}%"),
                models.Instrument.token_address.ilike(f"%{q}%"),
            ) if q else True
        ) \
        .filter(
            (
                models.Instrument.is_well_known == 1
            ) if show_well_known_only else True
        ) \
        .filter(models.Instrument.status == 'active') \
        .filter(
            # only show 
            models.InstrumentKPI_LatestPrice.date_as_of >= last_acceptable_price_update_date 
            if sort in ['price_change_perc_asc', 'price_change_perc_desc'] 
            else True
        ) \
        .filter(
            # only show instruments that gained for 'price_change_perc_asc'
            models.InstrumentKPI_LatestPrice.change_perc_1d >= 0 
            if sort == 'price_change_perc_desc'
            else True
        ) \
        .filter(
            # only show instruments that lost for 'price_change_perc_desc'
            models.InstrumentKPI_LatestPrice.change_perc_1d <= 0 
            if sort == 'price_change_perc_asc'
            else True
        ) \
        .order_by(order_by_param) \
        .offset(skip) \
        .limit(limit) \
        .all()


def get_instrument_by_id(db: Session, id: int):
    return db.query(models.Instrument) \
        .filter(models.Instrument.id == id) \
        .filter(models.Instrument.status == 'active') \
        .first()


def get_instrument_bars(db: Session, instrument_id: int, lookback_hours: int, bar_interval: str):

    lookback_date = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    print(lookback_date, bar_interval)

    return db.query(models.InstrumentKPI_PriceHistory) \
        .join(models.Instrument, models.InstrumentKPI_PriceHistory.instrument_id == models.Instrument.id) \
        .filter(models.Instrument.status == 'active') \
        .filter(
            models.InstrumentKPI_PriceHistory.instrument_id == instrument_id,
            models.InstrumentKPI_PriceHistory.timeframe == bar_interval,
            models.InstrumentKPI_PriceHistory.date_as_of >= lookback_date
        ) \
        .order_by(models.InstrumentKPI_PriceHistory.date_as_of) \
        .all()

def create_user(db: Session, user: models.User):
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_id(db: Session, id: int):
    return db.query(models.User).filter(models.User.id == id).first()

def get_all_users(db: Session):
    return db.query(models.User)

def get_account_by_user_id(db: Session, user_id: int, provider: str):
    return db.query(models.Account).filter(and_(
        models.Account.user_id == user_id,
        models.Account.provider == provider
    )).first()

def update_user_last_active_date(db: Session, user_id: int):
    user = get_user_by_id(db, user_id)
    user.date_last_active = func.now()
    db.merge(user)
    db.commit()
    db.refresh(user)
    return user

def set_user_last_seen_attributes(db: Session, user_id: int, app_version: Optional[str] = None, platform_name: Optional[str] = None):
    user = get_user_by_id(db, user_id)
    user.last_seen_app_version = app_version
    user.last_seen_platform = platform_name
    db.merge(user)
    db.commit()
    return user

def get_user_by_ext_user_id(db: Session, ext_user_id: str, provider: str):
    return db.query(models.User).join(models.Account).filter(and_(
        models.Account.ext_user_id == ext_user_id,
        models.Account.provider == provider
    )).first()

def set_investing_experience(db: Session, user_id: int, has_experience: bool):
    user = get_user_by_id(db, user_id)
    user.has_experience = int(has_experience)
    db.merge(user)
    db.commit()
    return user

def set_referrer_if_empty(db: Session, user_id: int, referrer_id: int):
    user = get_user_by_id(db, user_id)
    referrer = get_user_by_id(db, referrer_id)
    if referrer:
        user.referrer_id = referrer_id
        db.merge(user)
        db.commit()
    return user

def get_user_long_term_goal(db: Session, user_id: int):
    user = get_user_by_id(db, user_id)
    return user.target_net_worth_long_term

def set_user_long_term_goal(db: Session, user_id: int, target_net_worth: int):
    user = get_user_by_id(db, user_id)
    user.target_net_worth_long_term = int(target_net_worth)
    db.merge(user)
    db.commit()
    return user 


def set_user_dream_statement(db: Session, user_id: int, dream_statement: str):
    user = get_user_by_id(db, user_id)
    user.dream_statement = dream_statement
    db.merge(user)
    db.commit()
    return user 


def set_user_birth_year(db: Session, user_id: int, birth_year_estimated: int):
    user = get_user_by_id(db, user_id)
    user.birth_year_estimated = birth_year_estimated
    db.merge(user)
    db.commit()
    return user 


def set_user_commitment_level(db: Session, user_id: int, commitment_level: str):
    user = get_user_by_id(db, user_id)
    user.commitment_level = commitment_level
    db.merge(user)
    db.commit()
    return user 


def create_portfolio(
    db: Session,
    user_id: int,
    cash_balance: float,
    status: str,
    portfolio_req: api_schema.PortfolioCreate,
    ):
    portfolio = models.Portfolio(
        user_id=user_id,
        character_id=portfolio_req.character_id,
        name=portfolio_req.name.strip(),
        is_public=int(portfolio_req.is_public),
        cash_balance=cash_balance,
        status=status,
    )
    db.add(portfolio)
    db.commit()
    return portfolio


def get_portfolio_by_id(db: Session, id: int):
    return db.query(models.Portfolio).filter(models.Portfolio.id == id).first()
        

def get_portfolios_by_user_id(db: Session, q: Optional[str], target_user_id: int, requester_user_id: int, skip: int, limit: int):
    return db.query(models.Portfolio) \
        .filter (
            and_( # display only public portfolios or portfolios that belong to the requester
                models.Portfolio.user_id == target_user_id,
                models.Portfolio.is_public == 1 if target_user_id != requester_user_id else True
            )
        ) \
        .filter( # filter by portfolio name
            models.Portfolio.name.ilike(f"%{q}%") if q else True
        ) \
        .offset(skip).limit(limit).all()

def get_portfolios_leaderboard(db: Session, q: Optional[str], skip: int, limit: int):

    lookback_days = 10
    date_leaderboard_lookback = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    return db.query(models.Portfolio) \
        .join(models.PortfolioStats) \
        .filter ( # display only public portfolios or portfolios that belong to the requester
                models.Portfolio.is_public == 1
        ) \
        .filter( # filter by portfolio name
            models.Portfolio.name.ilike(f"%{q}%") if q else True
        ) \
        .filter( # remove inactive portfolios
            True if q else models.Portfolio.date_last_updated >= date_leaderboard_lookback
        ) \
        .order_by(models.PortfolioStats.total_gain.desc()) \
        .offset(skip).limit(limit).all()

def mark_portfolio_as_deleted(db: Session, id: int):
    portfolio = get_portfolio_by_id(db, id)
    portfolio.status = 'deleted'
    db.commit()
    return portfolio

def create_transaction(
    db: Session,
    portfolio_id: int,
    associated_instrument_id: Optional[int],
    transaction_type: str,
    quantity: float,
    message: Optional[str],
    ):
    try:        
        # add transaction to portfolio
        transaction = models.PortfolioTransaction(
            portfolio_id=portfolio_id,
            associated_instrument_id=associated_instrument_id,
            transaction_type=transaction_type,
            quantity=quantity,
            status='pending',
            message=message
        )

        db.add(transaction)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise
    return transaction

def get_portfolio_transaction_by_id(db: Session, id: int):
    return db.query(models.PortfolioTransaction).filter(models.PortfolioTransaction.id == id).first()

def execute_portfolio_transaction(db: Session, id: int):
    transaction = get_portfolio_transaction_by_id(db, id)
    portfolio = get_portfolio_by_id(db, transaction.portfolio_id)
    instrument = get_instrument_by_id(db, transaction.associated_instrument_id)
    holding = get_holding_by_id(db,
     portfolio_id=transaction.portfolio_id,
     instrument_id=transaction.associated_instrument_id
     )

    try:
        instrument_price = instrument.kpi_latest_price.price
        transaction.value = instrument_price * transaction.quantity

        if transaction.transaction_type == models.PortfolioTransactionTypeUserScope.BUY.value:
            # deduct cash balance
            portfolio.cash_balance -= transaction.value
            if portfolio.cash_balance < 0:
                raise SnipsInsuficientFundsError('Not enough funds to complete the transaction')

            # add purchase to portfolio
            if holding:
                book_cost = holding.quantity * holding.average_price
                new_book_cost = book_cost + transaction.value
                new_quantity = holding.quantity + transaction.quantity
                new_average_price = new_book_cost / new_quantity
                holding.quantity = new_quantity
                holding.average_price = new_average_price
            else:
                holding = models.Holding(
                    portfolio_id=transaction.portfolio_id,
                    instrument_id=transaction.associated_instrument_id,
                    quantity=transaction.quantity,
                    average_price=instrument_price,
                )
        elif transaction.transaction_type == models.PortfolioTransactionTypeUserScope.SELL.value:
            # deduct existing holdings
            if holding:
                if holding.quantity < transaction.quantity:
                    raise SnipsInsufficientInstrumentQuantityError('You do not own enough of this instrument to sell it')
                
                transaction.ex_avg_price = holding.average_price
                book_cost = holding.quantity * holding.average_price
                new_book_cost = book_cost - transaction.value
                new_quantity = holding.quantity - transaction.quantity
                if new_quantity == 0:
                    holding.quantity = 0
                    holding.average_price = 0
                    # or delete the holding?
                else:
                    new_average_price = new_book_cost / new_quantity
                    holding.quantity = new_quantity
                    holding.average_price = new_average_price
            else:
                raise SnipsInsufficientInstrumentQuantityError('You do not own enough of this instrument to sell it')

            # add cash balance
            portfolio.cash_balance += transaction.value

        transaction.status = 'executed'
        transaction.date_executed = datetime.now(tz=timezone.utc)

        db.merge(holding)
        db.merge(portfolio)
        db.merge(transaction)

        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise
    except SnipsError as e:
        db.rollback()
        raise
    return transaction

def get_holdings_by_portfolio_id(db: Session, portfolio_id: int, skip: int, limit: int, sort_by: str, sort_order: str, ignore_sold_off: bool):
    return db \
        .query(models.Holding) \
        .join(models.Instrument, models.Holding.instrument_id == models.Instrument.id) \
        .filter(models.Instrument.status == 'active') \
        .filter(models.Holding.portfolio_id == portfolio_id) \
        .filter(
            models.Holding.quantity > 0 if ignore_sold_off else True
        ) \
        .order_by(models.Holding.date_last_updated.desc()) \
        .offset(skip) \
        .limit(limit) \
        .all()

def get_holding_by_id(db: Session, portfolio_id: int, instrument_id: int):
    return db.query(models.Holding) \
        .join(models.Instrument, models.Holding.instrument_id == models.Instrument.id) \
        .filter(models.Instrument.status == 'active') \
        .filter(and_(
            models.Holding.portfolio_id == portfolio_id,
            models.Holding.instrument_id == instrument_id
        )).first()

def get_transactions_by_portfolio_id(db: Session, portfolio_id: int, skip: int, limit: int):
    return db.query(models.PortfolioTransaction) \
        .filter(models.PortfolioTransaction.portfolio_id == portfolio_id) \
        .offset(skip).limit(limit).all()

def get_transactions(db: Session, filter: str, sort: str, skip: int, limit: int):
    return db.query(models.PortfolioTransaction) \
        .join(models.Portfolio, models.PortfolioTransaction.portfolio_id == models.Portfolio.id) \
        .filter(
            models.Portfolio.is_public == 1
        ) \
        .filter(
            and_(
                models.PortfolioTransaction.status == 'executed',
                or_(
                    models.PortfolioTransaction.transaction_type == 'buy',
                    models.PortfolioTransaction.transaction_type == 'sell',
                )
            ) if filter == 'EXECUTED_TRADES' else True
        ) \
        .order_by(
            models.PortfolioTransaction.date_executed.desc()
            if sort == 'DESC' else
            models.PortfolioTransaction.date_executed.asc()
        ) \
        .offset(skip).limit(limit).all()

def get_characters(db: Session, skip: int, limit: int):
    return db.query(models.Character).offset(skip).limit(limit).all()

def get_character_by_id(db: Session, id: int):
    return db.query(models.Character).filter(models.Character.id == id).first()

def get_portfolio_stats(db: Session, portfolio_id: int):
    return db.query(models.PortfolioStats).filter(models.PortfolioStats.portfolio_id == portfolio_id).first()

def refresh_portfolio_stats(db: Session, portfolio_id: int, refresh_timeout: int):
    stats = get_portfolio_stats(db, portfolio_id)

    if not stats or ((stats.date_last_updated + timedelta(seconds=refresh_timeout)) < datetime.now(tz=timezone.utc)):

        available_cash = db \
            .query(func.sum(models.Portfolio.cash_balance)) \
            .filter(
                models.Portfolio.id == portfolio_id,
            ) \
            .scalar()

        sales_value = db \
            .query(func.sum(models.PortfolioTransaction.value)) \
            .filter(
                models.PortfolioTransaction.portfolio_id == portfolio_id,
                models.PortfolioTransaction.status == 'executed',
                models.PortfolioTransaction.transaction_type == 'sell') \
            .scalar() or 0

        book_cost = db \
            .query(func.sum(models.PortfolioTransaction.value)) \
            .filter(
                models.PortfolioTransaction.portfolio_id == portfolio_id,
                models.PortfolioTransaction.status == 'executed',
                models.PortfolioTransaction.transaction_type == 'buy') \
            .scalar() or 0

        current_value = db \
            .query(func.sum(models.Holding.quantity * models.InstrumentKPI_LatestPrice.price)) \
            .join(models.InstrumentKPI_LatestPrice, models.Holding.instrument_id == models.InstrumentKPI_LatestPrice.instrument_id) \
            .filter(models.Holding.portfolio_id == portfolio_id) \
            .scalar() or 0

        net_worth = current_value + available_cash    
        pnl = sales_value + current_value - book_cost

        print('available cash: ', available_cash)
        print('sales value', sales_value)
        print('book cost', book_cost)
        print('current value', current_value)
        print('net worth', net_worth)
        print('P&L', pnl)

        stats = models.PortfolioStats(
            portfolio_id=portfolio_id,
            total_net_worth=net_worth,
            total_book_value=book_cost,
            total_gain=pnl,
            date_last_updated=func.now()
        )

        db.merge(stats)
        db.commit()
    return stats


def get_skills_by_user_id(db: Session, target_user_id: int, skip: int, limit: int):

    user_skill_subq = db.query(models.UserSkill) \
        .filter(models.UserSkill.user_id == target_user_id) \
        .subquery()

    q = db \
        .query(models.Skill, user_skill_subq) \
        .outerjoin(
            user_skill_subq,
            user_skill_subq.c.skill_id == models.Skill.id
        ) \
        .filter(
            models.Skill.is_active == 1
        ) \
        .order_by(
            models.Skill.id.asc()
        ) \
        .offset(skip) \
        .limit(limit)

    return q.all()


def get_skill_by_key(db: Session, skill_key: str):
    return db \
        .query(models.Skill) \
        .filter(
            models.Skill.is_active == 1,
            models.Skill.skill_key == skill_key
        ) \
        .first()


def get_user_skill_by_key(db: Session, user_id: int, skill_key: str):
    return db \
        .query(models.UserSkill) \
        .join(models.Skill, models.Skill.id == models.UserSkill.skill_id) \
        .filter(
            models.Skill.is_active == 1,
            models.Skill.skill_key == skill_key,
            models.UserSkill.user_id == user_id
        ) \
        .first()


def mark_user_skill_as_discovered(db: Session, user_id: int, skill_key: str):
    user_skill = get_user_skill_by_key(db=db, user_id=user_id, skill_key=skill_key)
    if user_skill is None:
        skill = get_skill_by_key(db=db, skill_key=skill_key)
        user_skill = models.UserSkill(
            skill_id = skill.id,
            user_id = user_id,
            date_discovered = func.now(),
            date_last_updated = func.now()
        )
    elif user_skill.date_discovered is None:
        user_skill.date_discovered = func.now()
        user_skill.date_last_updated = func.now()
    
    db.merge(user_skill)
    db.commit()
    return user_skill



def mark_user_skill_with_quiz_timestamp(db: Session, user_id: int, skill_key: str):
    user_skill = get_user_skill_by_key(db=db, user_id=user_id, skill_key=skill_key)
    if user_skill is not None:
        user_skill.date_last_started_quiz = func.now()
        user_skill.date_last_updated = func.now()
        db.merge(user_skill)
        db.commit()
    return user_skill


def get_quiz_details(db: Session, skill_key: str):
    q = db \
    .query(models.QuizQuestion) \
    .join(
        models.Skill,
        models.Skill.id == models.QuizQuestion.skill_id
    ) \
    .filter(
        models.Skill.skill_key == skill_key
    ) \
    .order_by(
        models.QuizQuestion.id.asc()
    )
    return q.all()

def mark_user_skill_as_unlocked(db: Session, user_id: int, skill_key: str):
    user_skill = get_user_skill_by_key(db=db, user_id=user_id, skill_key=skill_key)
    if user_skill is not None:
        user_skill.date_last_unlocked = func.now()
        user_skill.date_last_updated = func.now()
        db.merge(user_skill)
        db.commit()
    return user_skill


def add_quiz_answer_attempt(db: Session, user_id: int, skill_key: str, question_id: int, answer_id: int):
    user_skill = get_user_skill_by_key(db=db, user_id=user_id, skill_key=skill_key)
    if user_skill is not None:
        user_quiz_answer = models.UserQuizAttempt(
            user_id=user_id,
            question_id=question_id,
            answer_id=answer_id,
        )
        db.add(user_quiz_answer)
        db.commit()
        return True
    return False

def set_portfolio_public(db: Session, portfolio_id: int, is_public: bool):
    db_portfolio = get_portfolio_by_id(db=db, id=portfolio_id)
    is_public = int(is_public)
    db_portfolio.is_public = is_public
    db.merge(db_portfolio)
    db.commit()
    return db_portfolio

def set_portfolio_name(db: Session, portfolio_id: int, name: str):
    db_portfolio = get_portfolio_by_id(db=db, id=portfolio_id)
    db_portfolio.name = name
    db.merge(db_portfolio)
    db.commit()
    return db_portfolio

def set_portfolio_character_id(db: Session, portfolio_id: int, character_id: int):
    character = get_character_by_id(db=db, id=character_id)
    db_portfolio = get_portfolio_by_id(db=db, id=portfolio_id)
    if character: # if character exists
        db_portfolio.character_id = character_id
        db.merge(db_portfolio)
        db.commit()
    return db_portfolio

def activate_push_token(db: Session, provider: str, token: str, user_id: int):
    push_token = models.UserPushToken(
        provider=provider,
        token=token,
        user_id=user_id,
        status='active',
        date_last_validated=func.now(),
        date_last_updated=func.now()
    )

    try:
        db.merge(push_token)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise SnipsError

    return push_token
    

def get_push_token(db: Session, provider: str, token: str):
    return db \
        .query(models.UserPushToken) \
        .filter(models.UserPushToken.provider == provider) \
        .filter(models.UserPushToken.token == token) \
        .first()


def disable_push_token(db: Session, provider: str, token: str):
    push_token = get_push_token(db=db, provider=provider, token=token)
    push_token.status = 'disabled'
    try:
        db.merge(push_token)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise SnipsError

    return push_token


def get_skills_list(db: Session, user_id: int, phase=enums.SkillsListPhase):
    q = db \
        .query(models.UserSkill, models.Skill.skill_key) \
        .outerjoin(
            models.Skill,
            models.UserSkill.skill_id == models.Skill.id
        ) \
        .filter(
            models.UserSkill.user_id == user_id
        ) \
        .filter(
            models.Skill.is_active == 1
        ) \
        .filter(
            ( models.UserSkill.date_discovered != None ) if phase == enums.SkillsListPhase.DISCOVERED else True
        ) \
        .filter(
            ( models.UserSkill.date_last_unlocked != None ) if phase == enums.SkillsListPhase.UNLOCKED else True
        ) \
        .order_by(
            models.Skill.id.asc()
        )

    results = q.all()
    return [ result.skill_key for result in results ]


def count_user_portfolios(db: Session, user_id: int):
    return db \
        .query(func.count(models.Portfolio.id)) \
        .select_from(models.Portfolio) \
        .filter(models.Portfolio.user_id == user_id) \
        .scalar()


def claim_portfolio_reward(db: Session, portfolio_id: int, reward_type: str, reward_amount: float):
    portfolio = get_portfolio_by_id(db=db, id=portfolio_id)
    try:     

        # deposit a reward to the portfolio and update last claimed date
        portfolio.cash_balance = portfolio.cash_balance + reward_amount
        portfolio.date_last_updated = func.now()
        if reward_type == 'REWARD_WEEKLY':
            portfolio.date_last_claimed_weekly_reward = func.now()
        elif reward_type == 'REWARD_DAILY':
            portfolio.date_last_claimed_daily_reward = func.now()
        elif reward_type == 'REWARD_INTRADAY':
            portfolio.date_last_claimed_intraday_reward = func.now()
        else:
            db.rollback()
            raise SnipsError
        
        db.merge(portfolio)

        # add transaction to portfolio
        transaction = models.PortfolioTransaction(
            portfolio_id=portfolio_id,
            associated_instrument_id=None,
            transaction_type=reward_type,
            quantity=reward_amount,
            value=reward_amount,
            status='executed',
            date_executed=func.now()
        )

        db.add(transaction)
        db.commit()
        return portfolio
    except SQLAlchemyError as e:
        db.rollback()
        raise SnipsError


def get_collections(db: Session, skip: int, limit: int):
    return db \
        .query(models.InstrumentCollection) \
        .filter(models.InstrumentCollection.is_active == 1) \
        .order_by(
            models.InstrumentCollection.priority.asc(),
            models.InstrumentCollection.display_name.asc()
        ) \
        .offset(skip) \
        .limit(limit) \
        .all()


def get_instruments_by_collection_id(db: Session, collection_id: int, q: Optional[str], skip: int, limit: int):
    return db.query(models.Instrument) \
        .join(models.InstrumentCollectionMembership, models.InstrumentCollectionMembership.instrument_id == models.Instrument.id) \
        .filter(models.InstrumentCollectionMembership.collection_id == collection_id) \
        .filter(
            or_(
                models.Instrument.symbol.ilike(f"%{q}%"),
                models.Instrument.name.ilike(f"%{q}%"),
                models.Instrument.subtitle.ilike(f"%{q}%"),
                models.Instrument.tags.ilike(f"%{q}%"),
            ) if q else True
        ) \
        .filter(models.Instrument.status == 'active') \
        .order_by(models.Instrument.name) \
        .offset(skip) \
        .limit(limit) \
        .all()


def credit_xp_by_user_id(db: Session, user_id: int, xp_amount: int, xp_reason: str, xp_detail: Optional[str]=None, referrer_level: Optional[int]=0):
    """
    To properly credit user's XP, it takes 3 steps:

    1. Create an XP transaction
    2. Increment user's total XP
    3. Increment user's weekly XP

    The latter two steps must be done carefully as to avoid race condition
    """

    if referrer_level > c.MAX_REFERRER_LEVEL:
        return
    
    next_referrer_level = referrer_level + 1

    # Create transaction
    transaction = models.XPTransaction(
        user_id=user_id,
        amount=xp_amount,
        reason=xp_reason,
        detail=xp_detail,
    )
    db.add(transaction)

    # Get user object + increment XP stats
    user = get_user_by_id(db=db, id=user_id)
    user.xp_total = models.User.xp_total + xp_amount
    user.xp_current_week = models.User.xp_current_week + xp_amount
    user.xp_current_season = models.User.xp_current_season + xp_amount
    db.merge(user)

    # Commit the changes
    db.commit()

    referrer_xp_amount = int(c.XP_CREDIT.REFERRER_YIELD_FACTOR * xp_amount)
    if referrer_xp_amount > 0 and user.referrer is not None:
        credit_xp_by_user_id(
            db=db,
            user_id=user.referrer_id,
            xp_amount=int(c.XP_CREDIT.REFERRER_YIELD_FACTOR * xp_amount),
            xp_reason=c.XP_REASON.REFERRER_YIELD,
            xp_detail=f"{xp_reason},XPT={transaction.id}",
            referrer_level=next_referrer_level
        )


def get_xp_leaderboard(db: Session, q: Optional[str], skip: int, limit: int, timeframe: str='weekly'):
    return db.query(models.Portfolio) \
        .join(models.User, models.Portfolio.user_id == models.User.id) \
        .filter ( # display only public active portfolios 
            models.Portfolio.is_public == 1,
            models.User.status == 'active',
            models.Portfolio.status == 'active'
        ) \
        .filter( # filter by portfolio name
            models.Portfolio.name.ilike(f"%{q}%") if q else True
        ) \
        .order_by(
            models.User.xp_current_season.desc() if timeframe == 'season' else
            models.User.xp_current_week.desc() if timeframe == 'weekly' else
            models.User.xp_total.desc()
        ) \
        .offset(skip) \
        .limit(limit) \
        .all()


def credit_xp_on_transaction_execute_if_eligible(db: Session, transaction_id: int):
    transaction = get_portfolio_transaction_by_id(db=db, id=transaction_id)
    if transaction is None:
        return False
    # c.XP_LIMIT.BUY_TRANSACTION_UNIQUE_ELIGIBLE_INSTRUMENTS

    date_24_hours_ago = datetime.now(tz=timezone.utc) - timedelta(hours=24)

    n_transactions_with_messages = db \
        .query(models.PortfolioTransaction) \
        .filter (
            models.PortfolioTransaction.portfolio_id == transaction.portfolio_id,
            models.PortfolioTransaction.status == 'executed',
            models.PortfolioTransaction.date_executed != None,
            models.PortfolioTransaction.message != None,
            models.PortfolioTransaction.associated_instrument_id != None,
            models.PortfolioTransaction.date_executed > date_24_hours_ago,
        ) \
        .count()
    
    # if this is the first purchase of the asset in 24 hours and there are 5 or less unique assets purchased in total
    if n_transactions_with_messages <= c.XP_LIMIT.FEED_MESSAGE_UNIQUE_TRANSACTIONS:
        user_id = transaction.portfolio.user_id
        credit_xp_by_user_id(
            db=db,
            user_id=user_id,
            xp_amount=c.XP_CREDIT.FEED_MESSAGE,
            xp_reason=c.XP_REASON.FEED_MESSAGE,
            xp_detail=f"TX={transaction.id}",
        )
        return True
    return False


def credit_xp_on_buy_if_eligible(db: Session, transaction_id: int):
    transaction = get_portfolio_transaction_by_id(db=db, id=transaction_id)
    if transaction is None:
        return False
    # c.XP_LIMIT.BUY_TRANSACTION_UNIQUE_ELIGIBLE_INSTRUMENTS

    date_24_hours_ago = datetime.now(tz=timezone.utc) - timedelta(hours=24)

    n_transactions_with_instrument = db \
        .query(models.PortfolioTransaction) \
        .filter (
            models.PortfolioTransaction.portfolio_id == transaction.portfolio_id,
            models.PortfolioTransaction.status == 'executed',
            models.PortfolioTransaction.date_executed != None,
            models.PortfolioTransaction.associated_instrument_id == transaction.associated_instrument_id,
            models.PortfolioTransaction.transaction_type == models.PortfolioTransactionTypeUserScope.BUY.value,
            models.PortfolioTransaction.date_executed > date_24_hours_ago,
        ) \
        .count()
    
    n_unique_instruments = db \
        .query(models.PortfolioTransaction) \
        .distinct(models.PortfolioTransaction.associated_instrument_id) \
        .filter (
            models.PortfolioTransaction.portfolio_id == transaction.portfolio_id,
            models.PortfolioTransaction.status == 'executed',
            models.PortfolioTransaction.date_executed != None,
            models.PortfolioTransaction.associated_instrument_id != None,
            models.PortfolioTransaction.transaction_type == models.PortfolioTransactionTypeUserScope.BUY.value,
            models.PortfolioTransaction.date_executed > date_24_hours_ago,
        ) \
        .count()


    
    # if this is the first purchase of the asset in 24 hours and there are 5 or less unique assets purchased in total
    if n_transactions_with_instrument == 1 and n_unique_instruments <= c.XP_LIMIT.BUY_TRANSACTION_UNIQUE_ELIGIBLE_INSTRUMENTS:
        user_id = transaction.portfolio.user_id
        credit_xp_by_user_id(
            db=db,
            user_id=user_id,
            xp_amount=c.XP_CREDIT.BUY_TRANSACTION,
            xp_reason=c.XP_REASON.BUY_TRANSACTION,
            xp_detail=f"TX={transaction.id}",
        )
        return True

    return False


def credit_xp_on_sell_if_eligible(db: Session, transaction_id: int):
    transaction = get_portfolio_transaction_by_id(db=db, id=transaction_id)
    if transaction is None:
        return False
 
    ex_avg_price = transaction.ex_avg_price
    sale_price = transaction.value / transaction.quantity
    gain = math.floor((sale_price - ex_avg_price) * transaction.quantity)
    if gain > 0:
        # print('gain > 0')
        date_24_hours_ago = datetime.now(tz=timezone.utc) - timedelta(hours=24)

        xp_credited_in_24_hrs = db \
            .query(func.sum(models.XPTransaction.amount)) \
            .filter (
                models.XPTransaction.user_id == transaction.portfolio.user_id,
                models.XPTransaction.reason == c.XP_REASON.SELL_ASSET_AT_PROFIT,
                models.XPTransaction.date_credited > date_24_hours_ago,
            ) \
            .scalar() or 0
        
        if xp_credited_in_24_hrs >= c.XP_LIMIT.SELL_AT_PROFIT_MAX_DAILY_XP:
            return False

        xp_amount = int(math.floor(c.XP_CREDIT.COLLECT_PROFIT * (gain / c.XP_LIMIT.SELL_AT_PROFIT_COINS_PER_XP)))
        if xp_credited_in_24_hrs + xp_amount > c.XP_LIMIT.SELL_AT_PROFIT_MAX_DAILY_XP:
            xp_amount = c.XP_LIMIT.SELL_AT_PROFIT_MAX_DAILY_XP - xp_credited_in_24_hrs
        
        credit_xp_by_user_id(
            db=db,
            user_id=transaction.portfolio.user_id,
            xp_amount=xp_amount,
            xp_reason=c.XP_REASON.SELL_ASSET_AT_PROFIT,
            xp_detail=f"TX={transaction.id}"
        )
        return True

    return False

def get_lesson_by_id(db: Session, lesson_id: int):
    return db \
        .query(models.Lesson) \
        .filter(
            models.Lesson.id == lesson_id
        ) \
        .first()


def get_user_lesson_by_id(db: Session, lesson_id: int, user_id: int):
    return db \
        .query(models.UserLesson) \
        .join(models.Lesson, models.Lesson.id == models.UserLesson.lesson_id) \
        .filter(
            models.Lesson.id == lesson_id,
            models.UserLesson.user_id == user_id
        ) \
        .first()

def mark_lesson_as_completed(db: Session, lesson_id: int, user_id: int):
    user_lesson = models.UserLesson(
        user_id = user_id,
        lesson_id = lesson_id,
        date_last_completed = func.now()
    )
    db.merge(user_lesson)
    db.commit()
    return user_lesson


def reduce_credits_by_user_id(db: Session, user_id: int, credit_amount: int):
    user = get_user_by_id(db=db, id=user_id)
    
    if user.credit_balance >= credit_amount:
        user.credit_balance = models.User.credit_balance - credit_amount
    else:
        user.credit_balance = 0

    db.merge(user)
    db.commit()
    db.refresh(user)
    return user


def add_credits_by_user_id(db: Session, user_id: int, credit_amount: int):
    user = get_user_by_id(db=db, id=user_id)
    
    user.credit_balance = models.User.credit_balance + credit_amount

    db.merge(user)
    db.commit()
    db.refresh(user)
    return user