API_VERSION = '1.0.0'
LOG_LEVEL = 'DEBUG'

# Boostrap files
BOOTSTRAP_FILE_INSTRUMENTS = 'app/api/data/bootstrap/instruments_v1.json'
BOOTSTRAP_FILE_CHARACTERS = 'app/api/data/bootstrap/characters_v1.json'

MAX_ELEMENTS_PER_PAGE = 100
ANONYMOUS_USER_TOKEN_EXPIRATION_HOURS = 720
VERIFIED_USER_TOKEN_EXPIRATION_HOURS = 2160

PORTFOLIO_STATS_UPDATE_TIMEOUT_SECONDS = 60
STALE_ACCOUNT_DAYS = 90

APPLE_BUNDLE_ID = 'app.snips'  # do not change

MAX_PORTFOLIOS_FREE_PLAN = 1
MAX_PORTFOLIOS_PREMIUM_PLAN = 5

REWARD_WEEKLY_FREE_PLAN = 1000.0  # pre-game: 500.0
REWARD_WEEKLY_PREMIUM_PLAN = 1000.0
REWARD_DAILY_FREE_PLAN = 100.0 # pre-game: 50.0
REWARD_DAILY_PREMIUM_PLAN = 100.0
REWARD_INTRADAY_FREE_PLAN = 50  # pre-game: 25.0
REWARD_INTRADAY_PREMIUM_PLAN = 50.0

MAX_REFERRER_LEVEL = 1

class AI_CREDIT:
    NEW_USER_ADD = 1000  # how much is credited to a new user
    PREMIUM_USER_ADD = 15000  # will change depending on the premium plan
    SEND_MESSAGE_FEE = 100  # cost of asking Snips AI


class XP_REASON:
    SIGNUP = 'SIGNUP'
    BUY_TRANSACTION = 'BUY_ASSET'
    SELL_ASSET_AT_PROFIT = 'SELL_ASSET_AT_PROFIT'
    COLLECT_REWARD = 'COLLECT_REWARD'
    UNLOCK_SKILL = 'UNLOCK_SKILL'
    COMPLETE_LESSON_FIRST_TIME = 'COMPLETE_LESSON_FIRST_TIME'
    FEED_MESSAGE = 'FEED_MESSAGE'
    REFEREE = 'REFEREE'  # user was referred by someone
    REFERRER_YIELD = 'REFERRER_YIELD'  # user receives a portion of their referees' XP
    AI_MESSAGE = 'AI_MESSAGE'

class XP_CREDIT:
    """
    Amount of XP credited for certain actions
    """
    SIGNUP = 500
    BUY_TRANSACTION = 500
    COLLECT_REWARD = 100
    UNLOCK_SKILL = 1000
    COLLECT_PROFIT = 100
    COMPLETE_LESSON_FIRST_TIME = 300
    FEED_MESSAGE = 200
    REFEREE = 10000
    AI_MESSAGE = 200
    REFERRER_YIELD_FACTOR = 0.1  # referrers get 10% of referees' XP


class XP_LIMIT:
    """
    Various XP limits
    """
    # daily limit for eligibility to receive a bonus from buy transactions
    BUY_TRANSACTION_UNIQUE_ELIGIBLE_INSTRUMENTS = 10
    # daily XP limit from selling assets at profit
    SELL_AT_PROFIT_MAX_DAILY_XP = 5000
    # how many coins are required to get 1 XP
    SELL_AT_PROFIT_COINS_PER_XP = 1
    # how many transactions do you get XP credited for when leaving a message/comment
    FEED_MESSAGE_UNIQUE_TRANSACTIONS = 10
