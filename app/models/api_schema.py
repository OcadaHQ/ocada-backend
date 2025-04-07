from optparse import Option
from typing import List, Dict, Optional
from datetime import datetime, date

from pydantic import BaseModel


class InstrumentKPI_LatestPrice(BaseModel):
    price: float
    change_perc_1d: float
    change_abs_1d: float
    date_as_of: datetime
    date_last_updated: datetime

    class Config:
        orm_mode = True


class InstrumentKPI_Summary(BaseModel):
    category: str
    fiscal: Optional[str]
    kpi_key: str
    kpi_value: str
    date_as_of: date
    date_last_updated: datetime

    class Config:
        orm_mode = True


class InstrumentBase(BaseModel):
    type: str
    name: str
    symbol: str


class InstrumentCollection(BaseModel):
    id: int
    key: str
    display_name: str
    is_premium: bool
    is_active: bool

    date_created: datetime
    date_last_updated: datetime

    class Config:
        orm_mode = True

class InstrumentKPI_TokenMetrics(BaseModel):
    market_cap: Optional[float]
    real_market_cap: Optional[float]
    holders: Optional[int]
    risk_score: Optional[int]
    liquidity: Optional[float]
    number_markets: Optional[int]
    date_as_of: datetime
    date_last_updated: datetime

    class Config:
        orm_mode = True
    

class InstrumentCreate(InstrumentBase):
    pass


class Instrument(InstrumentBase):
    id: int
    description: Optional[str]
    subtitle: Optional[str]
    image_url: Optional[str]
    is_well_known: bool

    token_address: Optional[str]
    token_chain: Optional[str]
    twitter_url: Optional[str]
    website_url: Optional[str]
    tg_url: Optional[str]
    discord_url: Optional[str]
    coingecko_id: Optional[str]
    medium_url: Optional[str]

    kpi_latest_price: Optional[InstrumentKPI_LatestPrice]
    kpi_summary: List[InstrumentKPI_Summary]
    kpi_token_metrics: Optional[InstrumentKPI_TokenMetrics]

    date_created: datetime
    date_last_updated: datetime

    class Config:
        orm_mode = True


class InstrumentPriceHistoryBar(BaseModel):
    timeframe: str

    price_open: float
    price_high: float
    price_low: float
    price_close: float
    transaction_volume: float

    date_as_of: datetime
    date_last_updated: datetime

    class Config:
        orm_mode = True


class InstrumentPriceHistory(BaseModel):
    bars: List[InstrumentPriceHistoryBar]

    class Config:
        orm_mode = True


# Users
class UserBase(BaseModel):
    id: int
    xp_total: int
    xp_current_week: int
    xp_current_season: int
    is_premium: bool


class User(UserBase):
    class Config:
        orm_mode = True


class ConnectedExternalUserAccountExposed(BaseModel):
    provider: str
    ext_user_id: str
    
    class Config:
        orm_mode = True


class ConnectedExternalUserAccount(BaseModel):
    provider: str
    user_id: int
    ext_user_id: str
    detail: str


class CurrentUser(UserBase):
    email: Optional[str]
    has_experience: Optional[bool]
    status: str
    secret_id: str
    credit_balance: int
    target_net_worth_long_term: Optional[str]
    accounts: List[ConnectedExternalUserAccountExposed]
    referrer_id: Optional[int]
    date_created: datetime
    date_last_active: datetime

    class Config:
        orm_mode = True


class DeletedUserConfirmation(BaseModel):
    user: CurrentUser
    deleted: bool
    detail: str

    class Config:
        orm_mode = True


class LoggedInUser(BaseModel):
    access_token: str
    token_type: str
    user: CurrentUser

    class Config:
        orm_mode = True


class Character(BaseModel):
    id: int
    image_url: Optional[str]
    category: str
    date_created: datetime
    date_last_updated: datetime

    class Config:
        orm_mode = True


class PortfolioStats(BaseModel):
    portfolio_id: int
    total_net_worth: Optional[float]
    total_book_value: Optional[float]
    total_gain: Optional[float]
    date_last_updated: datetime

    class Config:
        orm_mode = True


class XPTransaction(BaseModel):
    id: int
    user_id: int
    amount: int
    reason: str
    detail: Optional[str]
    date_credited: datetime
    # date_last_updated: datetime
    class Config:
        orm_mode = True

class PortfolioBase(BaseModel):
    character_id: int
    name: str
    is_public: bool


class PortfolioView(PortfolioBase):
    id: int
    user_id: int
    cash_balance: float
    status: str
    date_created: datetime
    date_last_updated: datetime
    character: Character
    stats: Optional[PortfolioStats]

    date_last_claimed_weekly_reward: Optional[datetime]
    date_last_claimed_daily_reward: Optional[datetime]
    date_last_claimed_intraday_reward: Optional[datetime]

    class Config:
        orm_mode = True

class PortfolioUserView(PortfolioView):
    user: User
    class Config:
        orm_mode = True

class PortfolioCreate(PortfolioBase):
    class Config:
        orm_mode = True


class PortfolioTransaction(BaseModel):
    id: int
    portfolio_id: int
    associated_instrument_id: int
    quantity: float
    value: Optional[float]
    ex_avg_price: Optional[float]
    transaction_type: str
    status: str
    message: Optional[str]

    date_created: datetime
    date_executed: Optional[datetime]

    class Config:
        orm_mode = True

class PortfolioTransactionDetailed(PortfolioTransaction):
    instrument: Optional[Instrument]
    portfolio: PortfolioView

    class Config:
        orm_mode = True


class Holding(BaseModel):
    portfolio_id: int
    instrument_id: int
    quantity: float
    average_price: float

    instrument: Instrument
    
    date_created: datetime
    date_last_updated: datetime

    class Config:
        orm_mode = True


class SkillGroup(BaseModel):
    id: int
    group_key: str
    description: str

    class Config:
        orm_mode = True


class UserSkill(BaseModel):
    user_id: int
    skill_id: int
    
    date_discovered: Optional[datetime]
    date_last_started_quiz: Optional[datetime]
    date_last_unlocked: Optional[datetime]
    date_last_updated: Optional[datetime]

    class Config:
        orm_mode = True


class QuizAnswer(BaseModel):
    id: int
    question_id: int
    answer_text: str
    is_correct: bool

    class Config:
        orm_mode = True


class QuizQuestion(BaseModel):
    id: int
    skill_id: int
    question: str
    quiz_answers: List[QuizAnswer]
    class Config:
        orm_mode = True


class Quiz(BaseModel):
    questions: QuizQuestion

    class Config:
        orm_mode = True


class Skill(BaseModel):
    id: int
    skill_key: str
    description: str
    is_discoverable: bool
    expiration_days: int
    is_active: bool
    date_created: datetime
    date_last_updated: datetime

    class Config:
        orm_mode = True


class SkillWithUser(Skill):
    user_skill: Optional[UserSkill]

    class Config:
        orm_mode = True

class SingleUserSkill(BaseModel):
    skill: Skill
    user_skill: UserSkill

    class Config:
        orm_mode = True

class SkillWithQuiz(Skill):
    quiz_questions: List[QuizQuestion]
    
    class Config:
        orm_mode = True

class QuizSubmissionInput(BaseModel):
    __root__: Dict[int, int]


class QuizSubmissionSummary(BaseModel):
    passed: bool
    passed_before: bool
    n_questions: int
    n_correct_answers: int

class QuizSubmissionResult(BaseModel):
    summary: QuizSubmissionSummary
    user_skill: Optional[UserSkill]

    class Config:
        orm_mode = True

class LogResponse(BaseModel):
    detail: str

    class Config:
        orm_mode = True


class UserSkillList(BaseModel):
    discovered: List[str]
    unlocked: List[str]

    class Config:
        orm_mode = True


# -------------- Learn --------------

class QuizAnswerView(BaseModel):
    id: int
    question_id: int
    answer_text: str
    is_correct: bool

    class Config:
        orm_mode = True


class QuizQuestionView(BaseModel):
    id: int
    lesson_id: int
    question_text: str
    quiz_answers: List[QuizAnswerView]
    class Config:
        orm_mode = True


class LessonView(BaseModel):
    id: int
    name: str
    lesson_text: Optional[str]
    lesson_image: Optional[str]
    priority: int

    quiz_questions: List[QuizQuestionView]

    class Config:
        orm_mode = True


class UserLessonView(BaseModel):
    user_id: int
    lesson_id: int
    
    date_last_completed: Optional[datetime]

    class Config:
        orm_mode = True


class SkillStatView(BaseModel):
    id: int
    name: str
    description: Optional[str]
    n_lesson_total: int
    n_lessons_completed: int

    class Config:
        orm_mode = True


class LessonSubmissionInput(BaseModel):
    __root__: Dict[int, int]


class LessonSubmissionSummary(BaseModel):
    passed: bool
    passed_before: bool
    n_questions: int
    n_correct_answers: int

class LessonSubmissionResult(BaseModel):
    lesson_id: int
    summary: LessonSubmissionSummary
    xp_credited: int

    class Config:
        orm_mode = True

class RewardClaimResponse(BaseModel):
    total_claimed: int
    xp_earned: int
