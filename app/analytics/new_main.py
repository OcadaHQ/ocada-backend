import os
from datetime import datetime, timedelta
import click

from sqlalchemy import create_engine, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.analytics.utils.cmc_api as cmc_api
import app.analytics.utils.birdeye_api as beye_api
from app.models.models import Base, Instrument

from app.models.models import Base, \
    Instrument, \
    InstrumentKPI_PriceHistory, \
    InstrumentKPI_LatestPrice, \
    InstrumentKPI_TokenMetrics

selected_instruments = [
    # 'wif'
]

@click.group()
def cli():
    pass

def create_session(db_host: str, db_port: str, db_user: str, db_pass: str, db_name):
    engine = create_engine(f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}')
    session = Session(engine, future=True)
    return session

@click.command()
def add_solana_tokens():
    print('Checking if there are new tokens to be added from "Solana Ecosystem" on Coinmarketcap')
    session = create_session(db_host=os.getenv('APP_DB_HOST', ''), db_port=os.getenv('APP_DB_PORT', ''), db_user=os.getenv('APP_DB_USER', ''), db_pass=os.getenv('APP_DB_PASSWORD', ''), db_name=os.getenv('APP_DB_NAME', ''))
    try:
        instruments = session.query(Instrument) \
            .filter(
                or_(
                    Instrument.token_chain == 'solana',
                )
            ) \
            .all()
        already_added_tokens = [instrument.token_address for instrument in instruments]
        solana_tokens = cmc_api.get_solana_tokens()
        for token in solana_tokens:
            if token['platform']['token_address'] not in already_added_tokens:
                add_new_token_to_db(token)
    except Exception as e:
        print(f"Failed to add Solana tokens. Error: {e}")
    session.close()

def add_new_token_to_db(token):
    print(f"Adding a new token {token['name']}: {token['platform']['token_address']}")
    session = create_session(db_host=os.getenv('APP_DB_HOST', ''), db_port=os.getenv('APP_DB_PORT', ''), db_user=os.getenv('APP_DB_USER', ''), db_pass=os.getenv('APP_DB_PASSWORD', ''), db_name=os.getenv('APP_DB_NAME', ''))
    try:
        address = token['platform']['token_address']
        overview = beye_api.get_token_overview_by_address(address)
        new_instrument = Instrument(
            type='crypto',
            name=token['name'],
            symbol=token['symbol'],
            cmc_rank=token['cmc_rank'],
            description=overview.get('extensions', {}).get('description'),
            image_url=overview.get('logoURI'),
            tags=', '.join(token.get('tags', [])),
            is_well_known=0,
            status='active',
            token_address=address,
            token_chain='solana',
            twitter_url=overview.get('extensions', {}).get('twitter'),
            website_url=overview.get('extensions', {}).get('website'),
            tg_url=overview.get('extensions', {}).get('telegram'),
            discord_url=overview.get('extensions', {}).get('discord'),
            coingecko_id=overview.get('extensions', {}).get('coingeckoId'),
            medium_url=overview.get('extensions', {}).get('medium')
        )
        session.add(new_instrument)
        session.commit()
    except Exception as e:
        print(f"Failed to add new token - {token['name']}: {token['platform']['token_address']}. Error: {e}")
    session.close()

@click.command()
@click.option('--timeframe', default='1D', help='Timeframe for price history data. Available options: 1m, 3m, 5m, 15m, 30m, 1H, 4H, 12H, 1D, 1W, 1M')
def update_price_history(timeframe='1D'):
    session = create_session(db_host=os.getenv('APP_DB_HOST', ''), db_port=os.getenv('APP_DB_PORT', ''), db_user=os.getenv('APP_DB_USER', ''), db_pass=os.getenv('APP_DB_PASSWORD', ''), db_name=os.getenv('APP_DB_NAME', ''))

    instruments = session.query(Instrument) \
        .filter(
            or_(
                Instrument.token_chain == 'solana',
            )
         ) \
        .all()

    for instrument in instruments:
        if instrument.symbol not in selected_instruments and len(selected_instruments) > 0:
            continue

        # get the last fetched timestamp from the database
        last_price_entry = session.query(InstrumentKPI_PriceHistory) \
            .filter_by(instrument_id=instrument.id, timeframe=timeframe) \
            .order_by(InstrumentKPI_PriceHistory.date_as_of.desc()) \
            .first()

        last_fetched_timestamp = last_price_entry.date_as_of if last_price_entry else None
        print(f'Last update: {last_fetched_timestamp}')

        # convert to unix timestamp 
        last_fetched_timestamp_unix = int(last_fetched_timestamp.timestamp()) if last_fetched_timestamp else None

        print(f'Updating price history ({timeframe}) for ticker: {instrument.symbol}')
        try:
            price_history_bars = beye_api.get_crypto_price_history(instrument.token_address, timeframe, last_fetched_timestamp_unix)
            # print(f'Price history bars: {price_history_bars}')
            for bar in price_history_bars['items']:
                session.merge(InstrumentKPI_PriceHistory(
                    instrument_id=instrument.id,
                    timeframe=timeframe,
                    date_as_of=datetime.utcfromtimestamp(bar['unixTime']),
                    price_open=bar['o'],
                    price_high=bar['h'],
                    price_low=bar['l'],
                    price_close=bar['c'],
                    transaction_volume=bar['v'],
                    date_last_updated=func.now()
                ))
            print(f'Updated price for {instrument.symbol}')
            session.commit()
        except Exception as e:
            print(f'Failed to update price history for {instrument.symbol}: {instrument.token_address}. Error: {e}')
    session.close()

@click.command()
def update_latest_price():
    print(f'Updating latest prices for all tokens...')
    session = create_session(db_host=os.getenv('APP_DB_HOST', ''), db_port=os.getenv('APP_DB_PORT', ''), db_user=os.getenv('APP_DB_USER', ''), db_pass=os.getenv('APP_DB_PASSWORD', ''), db_name=os.getenv('APP_DB_NAME', ''))
    instruments = session.query(Instrument) \
        .filter(
            or_(
                Instrument.token_chain == 'solana',
            )
         ) \
        .all()
    addresses = [instrument.token_address for instrument in instruments]
    latest_prices = beye_api.get_latest_crypto_price(addresses)
    for instrument in instruments:
        try:
            session.merge(InstrumentKPI_LatestPrice(
                instrument_id=instrument.id,
                date_as_of=datetime.utcfromtimestamp(latest_prices[instrument.token_address]['updateUnixTime']) if latest_prices[instrument.token_address]['updateUnixTime'] is not None else 0,
                price=latest_prices[instrument.token_address]['value'] if latest_prices[instrument.token_address]['value'] is not None else 0,
                change_abs_1d=0,
                change_perc_1d=latest_prices[instrument.token_address]['priceChange24h'] if latest_prices[instrument.token_address]['priceChange24h'] is not None else 0,
                date_last_updated=func.now()
            ))
            session.commit()
        except Exception as e:
            print(f'Failed to update latest price for {instrument.symbol}: {instrument.token_address}. Error: {e}')
    session.close()

@click.command()
def update_metrics():
    session = create_session(db_host=os.getenv('APP_DB_HOST', ''), db_port=os.getenv('APP_DB_PORT', ''), db_user=os.getenv('APP_DB_USER', ''), db_pass=os.getenv('APP_DB_PASSWORD', ''), db_name=os.getenv('APP_DB_NAME', ''))
    instruments = session.query(Instrument) \
        .filter(
            or_(
                Instrument.token_chain == 'solana',
            )
         ) \
        .all()
    for instrument in instruments:
        if instrument.symbol not in selected_instruments and len(selected_instruments) > 0:
            continue
        print(f'Updating metrics for ticker: {instrument.symbol}')
        try:
            token_info = beye_api.get_token_overview_by_address(instrument.token_address)
            risk_score_summary = beye_api.get_risk_score(instrument.token_address)
            session.merge(InstrumentKPI_TokenMetrics(
                    instrument_id=instrument.id,
                    date_as_of=func.now(),
                    market_cap=token_info['mc'],
                    real_market_cap=token_info['realMc'],
                    holders = token_info['holder'],
                    risk_score = risk_score_summary['score'],
                    liquidity = token_info['liquidity'],
                    number_markets = token_info['numberMarkets'],
                    date_last_updated=func.now()
                ))
            session.commit()
        except Exception as e:
            print(f'Failed to update metrics for {instrument.symbol}: {instrument.token_address}. Error: {e}')
    session.close()

@click.command()
def test():
    add_solana_tokens()
    update_price_history('5m')
    update_latest_price()
    update_metrics()

cli.add_command(add_solana_tokens)
cli.add_command(update_latest_price)
cli.add_command(update_metrics)
cli.add_command(test)
cli.add_command(update_price_history)

if __name__ == "__main__":
    cli()
    
    

