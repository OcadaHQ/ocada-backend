from enum import Enum
from sqlalchemy.orm import registry
from sqlalchemy.orm import relationship
from sqlalchemy import func
from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, Date, UniqueConstraint, ForeignKeyConstraint

# declarative base class
mapper_registry = registry()
Base = mapper_registry.generate_base()

class PortfolioTransactionTypeUserScope(Enum):
    """
    Portfolio transaction types that can be initiated by a user
    """
    BUY = 'buy'
    SELL = 'sell'

class PortfolioTransactionTypeAppScope(Enum):
    """
    Portfolio transaction types that are permitted in the scope of the application
    """
    BUY = 'buy'
    SELL = 'sell'
    DIVIDEND = 'dividend'
    BONUS = 'bonus'
    OTHER = 'other'
    REWARD_WEEKLY = 'REWARD_WEEKLY'
    REWARD_DAILY = 'REWARD_DAILY'


class User(Base):
    """
    A user represents a person using the application.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    display_name = Column(String, nullable=False, default='Player', server_default='Player')
    email = Column(String, nullable=True, unique=False)
    email_confirmed = Column(Integer, nullable=False, default=0, server_default='0')
    email_opt_out = Column(Integer, nullable=False, default=0, server_default='0')
    referrer_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, default=None, server_default=None)

    has_experience = Column(Integer, default=None, server_default=None)

    status = Column(String, nullable=False, default='active', server_default='active')
    secret_id = Column(String, nullable=False, default='user', server_default='user', comment='to be used by revenuecat')
    is_premium = Column(Integer, nullable=False, default=0, server_default="0") # 0: free, 1: premium
    credit_balance = Column(Integer, nullable=False, default=0, server_default="0")  # credits used for Snips AI

    xp_total = Column(Integer, nullable=False, default=0, server_default='0')  # total XP accumulated over lifetime
    xp_current_week = Column(Integer, nullable=False, default=0, server_default='0')  # total XP accumulated in the current week
    xp_current_season = Column(Integer, nullable=False, default=0, server_default='0')  # total XP accumulated in the current season

    birth_year_estimated = Column(Integer, nullable=True)
    dream_statement = Column(String, nullable=True, comment='what is the dream of the user')
    target_net_worth_long_term = Column(Integer, nullable=True)
    commitment_level = Column(String, nullable=True, comment='serious/casual')

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    date_last_active = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    last_seen_app_version = Column(String, nullable=True, default=None, server_default=None)
    last_seen_platform = Column(String, nullable=True, default=None, server_default=None, comment='ios/android')

    accounts = relationship('Account', backref='users', cascade='all, delete')
    achievements = relationship('UserAchievement', back_populates='users', cascade='all, delete')
    portfolios = relationship('Portfolio', back_populates='user', cascade='all, delete')

    user_push_tokens = relationship('UserPushToken', back_populates='user', cascade='all, delete')
    push_receipts = relationship('PushReceipt', back_populates='user', cascade='all, delete')

    xp_transactions = relationship('XPTransaction', back_populates='user', cascade='all, delete')
    xp_snapshot = relationship('XPSnapshot', back_populates='user', cascade='all, delete')
    user_lessons = relationship('UserLesson', back_populates='user', cascade='all, delete')
    referrer = relationship('User', remote_side=[id])


class Account(Base):
    """
    todo: add columns for openid 
    An account is used for OIDC authenticaiton
    """
    __tablename__ = 'accounts'
    provider = Column(String, nullable=False, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)

    ext_user_id = Column(String, nullable=False) # external user ID, e.g. 'sub' in JWT payload
    detail = Column(String, nullable=True)

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        # only a single external provider's account can be used to authenticate into the app
        UniqueConstraint("provider", "ext_user_id", name="_account_provider_ext_user_id_uc"),
    )

class Character(Base):
    """
    A character represents a specific game scenario.
    This table is a collection of all the characters in the game.
    """
    __tablename__ = 'characters'
    id = Column(Integer, primary_key=True)
    image_url = Column(String, nullable=True) # store the image url
    category = Column(String, nullable=False)

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    portfolios = relationship('Portfolio', back_populates='character', cascade='all, delete')

class Portfolio(Base):
    """
    A portfolio is an instance of a user+character combination.
    The same user can have multiple portfolios with the same character.
    """
    __tablename__ = 'portfolios'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    character_id = Column(Integer, ForeignKey('characters.id'))
    name = Column(String, nullable=False)
    cash_balance = Column(Float, nullable=False, default=0.0, server_default="0.0")
    is_risk_taker = Column(Integer, nullable=True)
    status = Column(String, nullable=False) # active, inactive, deleted
    
    is_public = Column(Integer, nullable=False, default=1, server_default="1") # 0: private, 1: public

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    date_last_claimed_weekly_reward = Column(DateTime(timezone=True), nullable=True)
    date_last_claimed_daily_reward = Column(DateTime(timezone=True), nullable=True)
    date_last_claimed_intraday_reward = Column(DateTime(timezone=True), nullable=True)

    user = relationship('User', back_populates='portfolios')
    character = relationship('Character', back_populates='portfolios')
    
    holdings = relationship('Holding', back_populates='portfolio', cascade='all, delete')
    portfolio_transactions = relationship('PortfolioTransaction', back_populates='portfolio', cascade='all, delete')
    stats = relationship('PortfolioStats', backref='portfolio', uselist=False, cascade='all, delete')

class PortfolioStats(Base):
    """
    (Relatively) frequently updated statistics for a portfolio.
    """
    __tablename__ = 'portfolio_stats'
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), primary_key=True)
    total_net_worth = Column(Float, nullable=True, default=None)     # total net worth including cash and holdings
    total_book_value = Column(Float, nullable=True, default=None)    # how much a user spent on stocks
    total_gain = Column(Float, nullable=True, default=None)          # profits and losses

    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Holding(Base):
    """
    Holdings represent the distribution of assets/instruments in a portfolio.
    """
    __tablename__ = 'holdings'
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), primary_key=True)
    instrument_id = Column(Integer, ForeignKey('instruments.id'), primary_key=True)
    quantity = Column(Float, nullable=False, default=0)
    average_price = Column(Float, nullable=False, default=0)

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    portfolio = relationship('Portfolio', back_populates='holdings')
    instrument = relationship('Instrument', back_populates='holdings')


class PortfolioTransaction(Base):
    """
    Transaction log for a portfolio.
    """
    __tablename__ = 'portfolio_transactions'
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'))
    associated_instrument_id = Column(Integer, ForeignKey('instruments.id'), nullable=True) # nullable for cash transactions
    quantity = Column(Float, nullable=False)
    value = Column(Float, nullable=True) # negative for sell, positive for buy, null = not executed yet
    ex_avg_price = Column(Float, nullable=True, default=None, comment='Average price of the holding BEFORE the transaction has been executed')
    transaction_type = Column(String) # buy, sell, dividend, etc.
    status = Column(String, nullable=False, default='pending') # pending, completed, failed
    message = Column(String, nullable=True, default=None, comment='Message/comment left by the user')

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_executed = Column(DateTime(timezone=True), nullable=True, server_default=None)

    portfolio = relationship('Portfolio', back_populates='portfolio_transactions')
    instrument = relationship('Instrument', back_populates='portfolio_transactions')


class Achievement(Base):
    """
    Available achievements.
    """
    __tablename__ = 'achievements'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    img_url = Column(String, nullable=False)
    status = Column(String, nullable=False) # active, inactive, deleted

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    users = relationship('UserAchievement', back_populates='achievements', cascade='all, delete')


class UserAchievement(Base):
    """
    Achievements earned by a user.
    Association table.
    """
    __tablename__ = 'user_achievements'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    achievement_id = Column(Integer, ForeignKey('achievements.id'), primary_key=True)
    date_achieved = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    users = relationship('User', back_populates='achievements')
    achievements = relationship('Achievement', back_populates='users')


### Instrument related schemas ###

class Instrument(Base):
    """
    Represents a financial instrument (stocks, bonds, crypto, funds etc.)
    todo: industry, sector, status (active, inactive, deleted)
    """
    __tablename__ = 'instruments'
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False, comment="category: stock, crypto, fund") # todo: add enum
    name = Column(String, nullable=False, comment="full name of the instrument")
    symbol = Column(String, nullable=False, comment="stock or crypto ticker symbol, e.g. AAPL or BTC")
    subtitle = Column(String, nullable=True, default=None, server_default=None, comment="2-3 word description of the instrument")
    description = Column(String, nullable=True, comment="description presented to the user")
    image_url = Column(String, nullable=True, comment="url to a logo representing the instrument")
    tags = Column(String, nullable=True, default=None, server_default=None, comment="comma separated list of tags for searching)")
    is_well_known = Column(Integer, nullable=False, default=0, server_default="0", comment="1: tutorial friendly, 0: otherwise")
    status = Column(String, nullable=False, default='active', server_default='active', comment="active, inactive, deleted")
    # New fields
    token_address = Column(String, nullable=True, default=None, server_default=None, comment="token contract address")
    token_chain = Column(String, nullable=True, default=None, server_default=None, comment="token chain")
    twitter_url = Column(String, nullable=True, default=None, server_default=None, comment="token twitter url")
    website_url = Column(String, nullable=True, default=None, server_default=None, comment="token website url")
    tg_url = Column(String, nullable=True, default=None, server_default=None, comment="token telegram url")
    discord_url = Column(String, nullable=True, default=None, server_default=None, comment="token discord url")
    coingecko_id = Column(String, nullable=True, default=None, server_default=None, comment="token coingecko id")
    medium_url = Column(String, nullable=True, default=None, server_default=None, comment="token medium url")
    cmc_rank = Column(Integer, nullable=True, default=None, server_default=None, comment="coinmarketcap rank")

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    holdings = relationship('Holding', back_populates='instrument', cascade='all, delete')
    portfolio_transactions = relationship('PortfolioTransaction', back_populates='instrument', cascade='all, delete')
    instrument_collection_memberships = relationship('InstrumentCollectionMembership', back_populates='instrument', cascade='all, delete')

    # Universal KPIs for any instrument
    kpi_summary = relationship('InstrumentKPI_Summary', back_populates='instrument', cascade='all, delete')
    kpi_latest_price = relationship('InstrumentKPI_LatestPrice', backref='instruments', uselist=False, cascade='all, delete')
    kpi_price_history = relationship('InstrumentKPI_PriceHistory', backref='instruments', cascade='all, delete')
    
    # Crypto KPIs
    kpi_token_metrics = relationship('InstrumentKPI_TokenMetrics', backref='instruments', uselist=False, cascade='all, delete')

    # Stock KPIs
    kpi_eps_fq = relationship('StockKPI_EPS_FQ', backref='instruments', cascade='all, delete')
    kpi_eps_fy = relationship('StockKPI_EPS_FY', backref='instruments', cascade='all, delete')
    kpi_balance_sheet = relationship('StockKPI_BalanceSheet', backref='instruments', cascade='all, delete')

class InstrumentKPI_Summary(Base):
    """
    Represents summary metrics for a financial instrument
    """
    __tablename__ = 'instrument_kpi_summary'
    instrument_id = Column(Integer, ForeignKey('instruments.id'), primary_key=True)
    category = Column(String, primary_key=True)
    fiscal = Column(String, primary_key=True)   # quarter, year, or null if irrelevant
    kpi_key = Column(String, primary_key=True)
    kpi_value = Column(String, nullable=False)  # string, bc the value is arbitrary
    date_as_of = Column(Date, nullable=True)

    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    instrument = relationship('Instrument', back_populates='kpi_summary')

class InstrumentKPI_LatestPrice(Base):
    """
    Represents the latest price for an instrument.
    """
    __tablename__ = 'instrument_kpi_latest_prices'
    instrument_id = Column(Integer, ForeignKey('instruments.id'), primary_key=True)
    price = Column(Float, nullable=False)
    change_perc_1d = Column(Float, nullable=False, default=0, server_default='0')
    change_abs_1d = Column(Float, nullable=False, default=0, server_default='0')
    
    date_as_of = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
class InstrumentKPI_TokenMetrics(Base):
    """
    Represents tokens metrics.
    """
    __tablename__ = 'instrument_kpi_token_metrics'
    instrument_id = Column(Integer, ForeignKey('instruments.id'), primary_key=True)
    market_cap = Column(Float, nullable=True, default=0, server_default='0')
    real_market_cap = Column(Float, nullable=True, default=0, server_default='0')
    holders = Column(Integer, nullable=True, default=0, server_default='0')
    risk_score = Column(Integer, nullable=True, default=0, server_default='0')
    liquidity = Column(Float, nullable=True, default=0, server_default='0')
    number_markets = Column(Integer, nullable=True, default=0, server_default='0')

    date_as_of = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class InstrumentKPI_PriceHistory(Base):
    """
    Represents the price history for an instrument.
    Follow the bar pattern: date, open, high, low, close, volume
    """
    __tablename__ = 'instrument_kpi_price_history'
    instrument_id = Column(Integer, ForeignKey('instruments.id'), primary_key=True)
    timeframe = Column(String, nullable=False, primary_key=True, comment="e.g. 1DAY, 1WEEK, 1MONTH, 1YEAR")
    date_as_of = Column(DateTime(timezone=True), primary_key=True, comment="date corresponding to the price")

    price_open = Column(Float, nullable=False)
    price_high = Column(Float, nullable=False)
    price_low = Column(Float, nullable=False)
    price_close = Column(Float, nullable=False)
    transaction_volume = Column(Float, nullable=False)

    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class StockKPI_EPS_FQ(Base):
    """
    Represents earnings per share (EPS) for an instrument in a fiscal QUARTER.
    """
    __tablename__ = 'stock_kpi_eps_fq'
    instrument_id = Column(Integer, ForeignKey('instruments.id'), primary_key=True)
    date_fiscal_ending = Column(Date, nullable=False, primary_key=True)
    date_reported = Column(Date, nullable=False, server_default=None)

    reported_eps = Column(Float, comment="EPS reported by the company")
    consensus_eps = Column(Float, comment="EPS based on analyst estimated consensus")

    surprise_abs = Column(Float, comment="absolute difference between reported and consensus EPS")
    surprise_perc = Column(Float, comment="percentage difference between reported and consensus EPS")

    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class StockKPI_EPS_FY(Base):
    """
    Represents earnings per share (EPS) for an instrument in a fiscal YEAR.
    """
    __tablename__ = 'stock_kpi_eps_fy'
    instrument_id = Column(Integer, ForeignKey('instruments.id'), primary_key=True)
    date_fiscal_ending = Column(Date, nullable=False, primary_key=True)

    reported_eps = Column(Float, comment="EPS reported by the company")

    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class StockKPI_BalanceSheet(Base):
    """
    Represents the balance sheet within a .
    """
    __tablename__ = 'stock_kpi_balance_sheet'
    instrument_id = Column(Integer, ForeignKey('instruments.id'), primary_key=True)
    date_fiscal_ending = Column(Date, nullable=False, primary_key=True)
    fiscal_period = Column(String, nullable=False, primary_key=True, comment="quarter, year")

    reported_currency = Column(String, comment="currency reported by the company")

    ### Assets ###
    total_assets = Column(Float, comment="Total assets")
    # Current assets
    current_assets = Column(Float, comment="Total current assets: anything that could be sold for cash within one year")
    cce = Column(Float, comment="Cash and cash equivalents that could be immediately converted to cash (bonds, etc.)")
    cash_and_short_term_investments = Column(Float, comment="Short term investments")
    inventory = Column(Float, comment="Inventory: goods and materials that are not ready to be sold")
    current_net_receivables = Column(Float, comment="Current net receivables: money owed to the company that will LIKELY be paid within one year")
    other_current_assets = Column(Float, comment="Other current assets: anything that is not listed above")

    # Noncurrent assets
    noncurrent_assets = Column(Float, comment="Total noncurrent assets: long-term assets value of which may only be recognised after one year")
    ppe = Column(Float, comment="Property, plant and equipment")
    accumulated_depreciation_amortization_ppe = Column(Float, comment="Accumulated depreciation and amortization of property, plant and equipment")
    intangible_assets = Column(Float, comment="Intangible assets: intangible assets that are not ready to be sold")
    intangible_assets_excluding_goodwill = Column(Float, comment="Intangible assets excluding goodwill")
    goodwill = Column(Float, comment="Goodwill: excess purchase price of another company (e.g. acq's IP, brand that are difficult to quantify)")
    total_investments = Column(Float, comment="Investments: investments that are not ready to be sold")
    long_term_investments = Column(Float, comment="Long term investments")
    short_term_investments = Column(Float, comment="Short term investments")
    other_noncurrent_assets = Column(Float, comment="Other noncurrent assets: anything that is not listed above")

    ### Liabilities ###
    total_liabilities = Column(Float, comment="Total liabilities")
    # Current liabilities
    current_liabilities = Column(Float, comment="Total current liabilities: any liabilities due within one year")
    current_accounts_payable = Column(Float, comment="Current accounts payable: money owed to the company that will LIKELY be paid within one year")
    deferred_revenue = Column(Float, comment="Deferred revenue: advance payments a company receives for products or services that are to be delivered or performed in the future")
    current_debt = Column(Float, comment="???")
    short_term_debt = Column(Float, comment="???")
    other_current_liabilities = Column(Float, comment="Other current liabilities: anything that is not listed above")

    # Noncurrent liabilities
    noncurrent_liabilities = Column(Float, comment="Total noncurrent liabilities: long-term liabilities due after one year")
    capital_lease_obligations = Column(Float, comment="Capital lease obligation: liability for temporary use of assets")
    long_term_debt = Column(Float, comment="Long term debt: long-term liabilities that mature for over a year")
    current_long_term_debt = Column(Float, comment="Current long term debt: long-term liabilities due within one year")
    noncurrent_long_term_debt = Column(Float, comment="Noncurrent long term debt: long-term liabilities due in over a year")
    short_long_term_debt = Column(Float, comment="???")
    other_noncurrent_liabilities = Column(Float, comment="Other noncurrent liabilities: anything that is not listed above")

    # Equity
    total_sharteholders_equity = Column(Float, comment="Total shareholders equity: owner's claim on assets after debt has been paid")
    treasury_stock = Column(Float, comment="Treasury stock: repurchased shares of the company (buyback)")
    retained_earnings = Column(Float, comment="Retained earnings: earnings that are not yet distributed to shareholders")
    common_stock = Column(Float, comment="Common stock: shares of the company")
    common_stock_outstanding = Column(Float, comment="Common stock outstanding: shares of the company that are not yet available for sale")

    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


# Push notifications
class UserPushToken(Base):
    __tablename__ = 'user_push_tokens'
    provider =  Column(String, primary_key=True)
    token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String, nullable=False) # active/disabled (managed by the user), notregistered (when expo push service confir)
    
    date_last_validated = Column(DateTime(timezone=True), nullable=False)
    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship('User', back_populates='user_push_tokens')


class PushReceipt(Base):
    __tablename__ = 'push_receipts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # the user a notification was sent to

    provider = Column(String, nullable=False)  # EXPO, APNS or FCM
    token = Column(String, nullable=False)

    push_ticket_id = Column(String, nullable=True)
    push_receipt_id =  Column(String, nullable=True)
    detail =  Column(String, nullable=True)  # the actual message or code

    date_sent = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_proxy_received = Column(DateTime(timezone=True), nullable=True)
    date_accepted = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship('User', back_populates='push_receipts')

    __table_args__ = (
        # composite foreign key to push notifications
        ForeignKeyConstraint(
            ["provider", "token"], ["user_push_tokens.provider", "user_push_tokens.token"]
        ),
    )


class InstrumentCollection(Base):
    """
    Collections of stocks
    """
    __tablename__ = 'instrument_collections'
    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    is_premium = Column(Integer, nullable=False, default=0, server_default="0")  # 1 = available to premium users only, 0 = available to all
    is_active = Column(Integer, nullable=False, default=1, server_default="1")  # 1 = listed on the app, 0 = hidden
    priority = Column(Integer, nullable=False, default=100, server_default="100")  # priority in which the collection is returned in search

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    instrument_collection_memberships = relationship('InstrumentCollectionMembership', back_populates='instrument_collection', cascade='all, delete')


class InstrumentCollectionMembership(Base):
    """
    Association table b/w Instrument and InstrumentCollection
    """
    __tablename__ = 'instrument_collection_memberships'
    collection_id = Column(Integer, ForeignKey('instrument_collections.id'), primary_key=True)
    instrument_id = Column(Integer, ForeignKey('instruments.id'), primary_key=True)

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    instrument = relationship('Instrument', back_populates='instrument_collection_memberships')
    instrument_collection = relationship('InstrumentCollection', back_populates='instrument_collection_memberships')


class XPTransaction(Base):
    """
    User history of XP credits
    """
    __tablename__ = 'xp_transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Integer, nullable=False, comment='How much is credited/debited')
    reason = Column(String, nullable=False, comment='Reason identifier')
    detail = Column(String, nullable=True, server_default=None, default=None, comment='Additional information')

    date_credited = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship('User', back_populates='xp_transactions')


class XPSnapshot(Base):
    """
    Snapshot of Top 100 players by XP in each competition period
    """
    __tablename__ = 'xp_snapshot'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    timeframe = Column(String, nullable=False, primary_key=True, comment="e.g. 1W, 2W, 1M")
    date_as_of = Column(DateTime(timezone=True), primary_key=True, comment="when the snapshot was taken")

    xp_collected = Column(Integer, nullable=False, comment='XP collected in each period')

    user = relationship('User', back_populates='xp_snapshot')


# Snips Learn
class Skill(Base):
    __tablename__ = 'skills'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    lesson_skills = relationship('LessonSkill', back_populates='skill', cascade='all, delete')


class Lesson(Base):
    __tablename__ = 'lessons'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    lesson_text = Column(String, nullable=False)
    lesson_image = Column(String, nullable=True)

    priority = Column(Integer, nullable=False, default=100, server_default="100")

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user_lessons = relationship('UserLesson', back_populates='lesson', cascade='all, delete')
    lesson_skills = relationship('LessonSkill', back_populates='lesson', cascade='all, delete')
    quiz_questions = relationship('QuizQuestion', back_populates='lesson', cascade='all, delete')

class QuizQuestion(Base):
    __tablename__ = 'quiz_questions'
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'))
    question_text = Column(String, nullable=False)

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    lesson = relationship('Lesson', back_populates='quiz_questions')
    quiz_answers = relationship('QuizAnswer', back_populates='quiz_question', cascade='all, delete')


class QuizAnswer(Base):
    __tablename__ = 'quiz_answers'
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('quiz_questions.id'))
    answer_text = Column(String, nullable=False)    
    is_correct = Column(Integer, nullable=False, default=0, comment="")

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    quiz_question = relationship('QuizQuestion', back_populates='quiz_answers')

class UserLesson(Base):
    """
    Represents a relationship between a user and the skill they've acquired
    """
    __tablename__ = 'user_lessons'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), primary_key=True)

    date_last_completed = Column(DateTime(timezone=True), nullable=True, server_default=None)

    user = relationship('User', back_populates='user_lessons')
    lesson = relationship('Lesson', back_populates='user_lessons')


class LessonSkill(Base):
    """
    Association table between lessons and skills they contribute to
    """
    __tablename__ = 'lesson_skills'
    skill_id = Column(Integer, ForeignKey('skills.id'), primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), primary_key=True)

    date_created = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    skill = relationship('Skill', back_populates='lesson_skills')
    lesson = relationship('Lesson', back_populates='lesson_skills')