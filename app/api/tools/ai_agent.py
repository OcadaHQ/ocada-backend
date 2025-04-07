import os
import json
import requests

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory

from app.api import crud
from app.models import models
from app.api.firebase_custom_client import client_instance as fcc


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PRIMARY_MODEL = os.getenv("OPENAI_MODEL_NAME")

# knowledge base
KB_URL = os.getenv("KB_URL")

class AIAgent:
    def __init__(self, db_session, recent_messages, user_meta_data, portfolio_id):
        self.llm = ChatOpenAI(model=PRIMARY_MODEL, temperature=0.4)
        self.memory = ConversationBufferMemory(memory_key="chat_history")
        self.recent_messages = recent_messages
        self.db_session = db_session
        self.user_meta_data = user_meta_data
        self.portfolio_id = portfolio_id
        
        @tool
        def query_tokens(
                query: str
            ) -> list:
            """
            Desc:
                Provides list of token dicts that satisfy the query and currently supported by Ocada App.
            Args:
                query (str): either a contract address, name, or ticker symbol (prefferably contract address when have a choice)
            Returns:
                list: list of token dicts with ticker, internal ID, address, twitter, telegram, website, current price, mc, num of holders            
            """
            print('query:', query)
            db_instruments = crud.get_instruments(db=self.db_session, q=query.strip(), sort='cmc_rank', show_well_known_only=None, skip=0, limit=5)
            # Extract necessary information
            result = []
            for instrument in db_instruments:
                instrument_data = {
                    "type": instrument.type,  # Assuming there's a type attribute
                    "name": instrument.name,
                    "symbol": instrument.symbol,
                    "id": instrument.id,
                    #"description": instrument.description,
                    #"subtitle": instrument.subtitle,
                    #"image_url": instrument.image_url,
                    #"is_well_known": instrument.is_well_known,
                    "token_address": instrument.token_address,
                    "token_chain": instrument.token_chain,
                    "twitter_url": instrument.twitter_url,
                    "website_url": instrument.website_url,
                    "tg_url": instrument.tg_url,
                    "discord_url": instrument.discord_url,
                    # "coingecko_id": instrument.coingecko_id,
                    # "medium_url": instrument.medium_url,
                    "latest_price": {
                        "price": instrument.kpi_latest_price.price,
                        "change_perc_1d": instrument.kpi_latest_price.change_perc_1d,
                        "change_abs_1d": instrument.kpi_latest_price.change_abs_1d,
                        "date_as_of": instrument.kpi_latest_price.date_as_of.isoformat(),
                        "date_last_updated": instrument.kpi_latest_price.date_last_updated.isoformat()
                    },
                    "token_metrics": {
                        # "market_cap": instrument.kpi_token_metrics.market_cap,
                        "real_market_cap": instrument.kpi_token_metrics.real_market_cap,
                        "holders": instrument.kpi_token_metrics.holders,
                        "risk_score": instrument.kpi_token_metrics.risk_score,
                        "liquidity": instrument.kpi_token_metrics.liquidity,
                        "number_markets": instrument.kpi_token_metrics.number_markets,
                        # "date_as_of": instrument.kpi_token_metrics.date_as_of.isoformat(),
                        "date_last_updated": instrument.kpi_token_metrics.date_last_updated.isoformat()
                    },
                    #"date_created": instrument.date_created.isoformat(),
                    #"date_last_updated": instrument.date_last_updated.isoformat()
                }
                result.append(instrument_data)
            print(result)
            return result
        
        @tool
        def query_token_by_id(
                id: int
            ) -> dict:
            """
            Desc:
                Provides infomramtion for a specific token
            Args:
                id (int): internal id

            Returns:
                dict: dict with ticker, address, twitter, telegram, website, current price, market cap, number of holders
            """
            print('query id:', id)
            instrument = crud.get_instrument_by_id(db=self.db_session, id=id)
            # Extract necessary information
            instrument_data = {}
            if (instrument):
                instrument_data = {
                    "type": instrument.type,  # Assuming there's a type attribute
                    "name": instrument.name,
                    "symbol": instrument.symbol,
                    "id": instrument.id,
                    #"description": instrument.description,
                    #"subtitle": instrument.subtitle,
                    #"image_url": instrument.image_url,
                    #"is_well_known": instrument.is_well_known,
                    "token_address": instrument.token_address,
                    "token_chain": instrument.token_chain,
                    "twitter_url": instrument.twitter_url,
                    "website_url": instrument.website_url,
                    "tg_url": instrument.tg_url,
                    "discord_url": instrument.discord_url,
                    # "coingecko_id": instrument.coingecko_id,
                    # "medium_url": instrument.medium_url,
                    "latest_price": {
                        "price": instrument.kpi_latest_price.price,
                        "change_perc_1d": instrument.kpi_latest_price.change_perc_1d,
                        "change_abs_1d": instrument.kpi_latest_price.change_abs_1d,
                        "date_as_of": instrument.kpi_latest_price.date_as_of.isoformat(),
                        "date_last_updated": instrument.kpi_latest_price.date_last_updated.isoformat()
                    },
                    "token_metrics": {
                        # "market_cap": instrument.kpi_token_metrics.market_cap,
                        "real_market_cap": instrument.kpi_token_metrics.real_market_cap,
                        "holders": instrument.kpi_token_metrics.holders,
                        "risk_score": instrument.kpi_token_metrics.risk_score,
                        "liquidity": instrument.kpi_token_metrics.liquidity,
                        "number_markets": instrument.kpi_token_metrics.number_markets,
                        # "date_as_of": instrument.kpi_token_metrics.date_as_of.isoformat(),
                        "date_last_updated": instrument.kpi_token_metrics.date_last_updated.isoformat()
                    },
                    #"date_created": instrument.date_created.isoformat(),
                    #"date_last_updated": instrument.date_last_updated.isoformat()
                }
            print(instrument_data)
            return instrument_data
        
        @tool
        def buy_or_sell_token(
                token_id: int, 
                operation: str,
                quantity: float,
                rationale: str
            ) -> bool:
            """
            Desc:
                Buys or sells the token if there are enough money on user's balance and token is real. Before proceeding with the operation - you need to find out WHY the user wants it.
            Args:
                token_id (int): queried internal token id from "query_tokens()"
                operation (str): 'buy' or 'sell'
                quantity (float): number of tokens to buy, can be counted by count_quantity()"
                rationale (str): short text message that explains WHY a user decided to buy or sell 

            Returns:
                bool: success or not
            """
            print(token_id, operation, quantity, rationale)
            transaction_type = models.PortfolioTransactionTypeUserScope.BUY if operation == 'buy' else models.PortfolioTransactionTypeUserScope.SELL
            try:
                transaction = crud.create_transaction(
                    db=self.db_session,
                    portfolio_id=self.portfolio_id,
                    associated_instrument_id=token_id,
                    transaction_type=transaction_type.value,  # unpack enum
                    quantity=quantity,
                    message=rationale
                )
            except Exception as e:
                print(e)
                # raise HTTPException(
                #     status_code=400, detail="Could not create a transaction")
                return False
            if transaction:
                try:
                    executed_transaction = crud.execute_portfolio_transaction(
                        db=self.db_session,
                        id=transaction.id,
                    )
                except Exception as e:
                    print(e)
                    return False
            return True
        
        @tool
        def count_quantity(
            price: float,
            usd_amount: float,
        ) -> float:
            """
            Desc:
                Counts how many tokens fit per particular amount of USD
            Args:
                price (float): a token price, must be bigger than 0
                usd_amount (float): required usd amount, minimal amount is 1 USD

            Returns:
                float: quantity of tokens that fit 
            """
            if (usd_amount > 1) and (price > 0):
                return round((usd_amount-0.5)/price)
            return 0

        @tool
        def analyse_token_transactions(
            solana_token_addr: str
        ) -> list:
            """
            Desc:
                Checks last 100 transactions (events) for token and classifies the trades and makers types.
                Each trade can have next kind of type:
                  - positive pnl: take_profit, partial_take_profit, position_increase
                  - negative pnl: dca, take_loss
                  - no clear pnl: exit_position.
                Also, based on total investment into the token each maker is classified as:
                 - "shrimp" if invested $0-300
                 - "fish" if invested $300-3K
                 - "dolphin" if invested $3k-10K
                 - "whale" if invested $10K+.
                Trades with "funds_moved" - mean funds transsferred from a different wallet (cant count pnl)
                All events have a particular timestamp, so you can see the price trend.
                REMEMBER: Most of all you must focus on whales, dolphins, and fishes moves. You should help to understand whether there is a trend. Mention particular maker addresses if they have big impact.

            Args:
                solana_token_addr (str): real solana token address

            Returns:
                list of events
            """
            url = f"{KB_URL}/transactionsAnalytics"
            params = {'address': solana_token_addr.strip()}
            response = requests.get(url, params=params, timeout=60)

            if response.status_code == 200:
                return response.json()  # Assuming the response is in JSON format
            else:
                return []

        @tool
        def calculate_live_wallet_pnl(
            solana_wallet_addr: str
        ) -> dict:
            """
            Desc:
                Calculates Solana live wallet PnL, success rate, ROI, number of trades, total volume (based on dex trades only)
            Args:
                solana_wallet_addr (str): real solana wallet address

            Returns:
                wallet PnL summary: total_profit_usd, profit_realized_usd, profit_unrealized_usd, total_roi_perc, roi_realized_perc,
                roi_unrealized_perc, success_rate_perc, successful_trade_count, unsuccessful_trade_count, trading_volume_usd, total_trades_count,
                avg_trade_size_usd
            """
            url = f"{KB_URL}/walletAnalytics"
            params = {'address': solana_wallet_addr.strip()}
            response = requests.get(url, params=params, timeout=60)

            if response.status_code == 200:
                return response.json()  # Assuming the response is in JSON format
            else:
                return {}

        @tool
        def analyze_token_twitter_account_activity(
            twitter_username: str
        ) -> dict:
            """
            Desc:
                Calculates statistics for a twitter account, checking the followers, following and posts (tweets) metrics and trends over time
            Args:
                twitter_username (str): real twitter username

            Returns:
                twitter statistics: user_created_date, followers/following count, rank, last_30_days_count, last_30_days_change_perc, monthly gain trend
            """
            url = f"{KB_URL}/twitterAnalytics"
            params = {'username': twitter_username.strip()}
            response = requests.get(url, params=params, timeout=60)

            if response.status_code == 200:
                return response.json()  # Assuming the response is in JSON format
            else:
                return {}
        
        @tool
        def get_user_meta_data() -> dict:
            """
            Desc:
                Returns current user's meta data including: vritual portfolio, virtual USD balance, live solana wallet address, and goal if set.

            Returns:
                User specific meta data: vritual portfolio, virtual USD balance, live solana wallet address, and goal if set

            """
            return self.user_meta_data

        self.tools = [query_tokens, buy_or_sell_token, count_quantity, query_token_by_id, calculate_live_wallet_pnl, analyse_token_transactions, analyze_token_twitter_account_activity, get_user_meta_data] 

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", 
                 "You are an Ocada-AI assitant that lives inside of Ocada App and operates with a set of tools that can do different on-chain and off-chain analytics.\n\
                     Currently you are in development stage and you learn by collecting data and serving crypto degens to do virtual trading with Solana meme coins in DEX envirvonment. \n\
                     You currently have access to ~3000 most biggest tokens on Solana. You can do next by using the tools: \n\
                        - query token details information (contract address, internal id, price, market cap, twitter username, and more) by CA, name, or ticker (or by internal ID when it is known) \n\
                        - buy and sell virtual tokens on users behalf \n\
                        - analyze real Solana wallets PnL (please suggest users how improve their strategy along with analysis) \n\
                        - analyze twitter account activity for Solana tokens (offer this in order to analyze tokens fundamentals - yeah social are the only fundamentals for meme coins), pay attention to the dynamic it is considered healthy when the activity and number of followers is growing. \n\
                        - analyze token transactions: call 'analyse_token_transactions' and focus on largest moves (whales, dolphins) - ALWAYS call particular MAKERS addresses and sums, focus on FACTS and interpret them. \n\
                        - if you need users meta data such as virtual portfolio, virtual USD balance or live Solana Wallet address - you should use 'get_user_meta_data' tool. \n\
                    All these operations are 100% safe because you are working with a virtual wallet.\n\
                    If users ask for something that you cant do yet - promise this functionatlity in near future.\n\
                    Aks questions, guide users in crypto world. Be concise. Stay bullish on Ocada! \n\
                    STRICTLY USE NO MARKDOWN LANGUAGE AT ALL. If any links are included in the response - provide them as is (no square brackets). \n\
                    "),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )
        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)
        self.chat_histories = {}


    def process_message(self, sender_id, incoming_message):
        try:
            print(f'current history: \n{self.recent_messages}')
            # print(f'current questions: \n{self.mentica_criteria}')
            response = self.agent_executor.invoke(
                {
                    "input": incoming_message,
                    "chat_history": self.recent_messages,
                    # "mentica_criteria": self.mentica_criteria,
                }
            )
            print(response)
            agent_response = response.get('output', 'Sorry, I am on maintenance now.')
        except Exception as e:
            print(f"Error processing request: {str(e)}")
            agent_response = "Sorry, I couldn't process your request."
        return agent_response