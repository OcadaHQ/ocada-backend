import os

import click

from sqlalchemy import create_engine, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.analytics.constants as c
from app.analytics.utils.stock_api import StockAPI
from app.analytics.utils.crypto_api import CryptoAPI
from app.models.models import Base, \
    Instrument, \
    StockKPI_BalanceSheet, \
    StockKPI_EPS_FQ, \
    StockKPI_EPS_FY, \
    InstrumentKPI_PriceHistory, \
    InstrumentKPI_LatestPrice, \
    InstrumentKPI_Summary

from app.analytics.utils.helpers import get_recent_growth_pattern, get_recent_positive_pattern, rfc3339_to_datetime

selected_instruments = [
    # 'BTC'
]

@click.group()
def cli():
    pass

def create_session(db_host: str, db_port: str, db_user: str, db_pass: str, db_name):
    engine = create_engine(f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}')
    session = Session(engine, future=True)
    return session

@click.command()
@click.option('--alpaca-api_key_id', required=True, default=os.getenv('ALPACA_API_KEY_ID', ''))
@click.option('--alpaca-secret_key', required=True, default=os.getenv('ALPACA_SECRET_KEY', ''))
def list_available_crypto_assets(alpaca_api_key_id: str, alpaca_secret_key: str) -> None:
    
    crypto_api = CryptoAPI(
        alpaca_api_key_id=alpaca_api_key_id,
        alpaca_secret_key=alpaca_secret_key
    )

    assets = crypto_api.get_crypto_assets()
    for asset in assets:
        print(asset['class'], asset['exchange'], asset['status'], asset['symbol'], asset['name'])


@click.command()
@click.option('--db-host', required=True, default=os.getenv('APP_DB_HOST', ''))
@click.option('--db-port', required=True, default=os.getenv('APP_DB_PORT', ''))
@click.option('--db-user', required=True, default=os.getenv('APP_DB_USER', ''))
@click.option('--db-pass', required=True, default=os.getenv('APP_DB_PASSWORD', ''))
@click.option('--db-name', required=True, default=os.getenv('APP_DB_NAME', ''))
@click.option('--av-api_key', required=True, default= os.getenv('ALPHAVANTAGE_API_KEY', ''))
@click.option('--alpaca-api_key_id', required=True, default=os.getenv('ALPACA_API_KEY_ID', ''))
@click.option('--alpaca-secret_key', required=True, default=os.getenv('ALPACA_SECRET_KEY', ''))
def update_latest_price(
    db_host: str, db_port: str, db_user: str, db_pass: str, db_name: str,
    av_api_key: str, alpaca_api_key_id: str, alpaca_secret_key: str) -> None:
    
    session = create_session(db_host=db_host, db_port=db_port, db_user=db_user, db_pass=db_pass, db_name=db_name)

    stock_api = StockAPI(
        av_api_key=av_api_key,
        alpaca_api_key_id=alpaca_api_key_id,
        alpaca_secret_key=alpaca_secret_key
    )

    crypto_api = CryptoAPI(
        alpaca_api_key_id=alpaca_api_key_id,
        alpaca_secret_key=alpaca_secret_key
    )


    instruments = session.query(Instrument) \
        .filter(
            or_(
                Instrument.status == 'active',
                Instrument.status == 'prerelease',
            )
         ) \
        .all()

    for instrument in instruments:
        if instrument.symbol not in selected_instruments and len(selected_instruments) > 0:
            continue
        print(f'Ticker: {instrument.symbol}')
        try:

            if instrument.type == 'stock':
                kpi_latest_price = stock_api.get_latest_stock_price(instrument.symbol)
            elif instrument.type == 'crypto':
                kpi_latest_price = crypto_api.get_latest_crypto_price(symbol=instrument.symbol)
            
            print('Price:', kpi_latest_price)


            previous_price = session \
                .query(InstrumentKPI_PriceHistory) \
                .filter(
                    InstrumentKPI_PriceHistory.instrument_id == instrument.id,
                    func.date(InstrumentKPI_PriceHistory.date_as_of) < func.date(kpi_latest_price['as_of'])
                ) \
                .order_by(InstrumentKPI_PriceHistory.date_as_of.desc()) \
                .first()
            
            change_abs_1d = 0
            change_perc_1d = 0
            if kpi_latest_price.get('price', None) is not None and previous_price is not None and previous_price.price_close > 0:
                change_abs_1d = kpi_latest_price['price'] - previous_price.price_close
                change_perc_1d = round(change_abs_1d / previous_price.price_close * 100, 2)

            session.merge(InstrumentKPI_LatestPrice(
                instrument_id=instrument.id,
                date_as_of=kpi_latest_price['as_of'],
                price=kpi_latest_price['price'],
                change_abs_1d=change_abs_1d,
                change_perc_1d=change_perc_1d,
                date_last_updated=func.now()
            ))

            session.commit()

        except Exception as e:
            print(e)
    session.close()


@click.command()
@click.option('--db-host', required=True, default=os.getenv('APP_DB_HOST', ''))
@click.option('--db-port', required=True, default=os.getenv('APP_DB_PORT', ''))
@click.option('--db-user', required=True, default=os.getenv('APP_DB_USER', ''))
@click.option('--db-pass', required=True, default=os.getenv('APP_DB_PASSWORD', ''))
@click.option('--db-name', required=True, default=os.getenv('APP_DB_NAME', ''))
@click.option('--av-api_key', required=True, default= os.getenv('ALPHAVANTAGE_API_KEY', ''))
@click.option('--alpaca-api_key_id', required=True, default=os.getenv('ALPACA_API_KEY_ID', ''))
@click.option('--alpaca-secret_key', required=True, default=os.getenv('ALPACA_SECRET_KEY', ''))
def update_price_history(
    db_host: str, db_port: str, db_user: str, db_pass: str, db_name: str,
    av_api_key: str, alpaca_api_key_id: str, alpaca_secret_key: str) -> None:
    
    session = create_session(db_host=db_host, db_port=db_port, db_user=db_user, db_pass=db_pass, db_name=db_name)

    stock_api = StockAPI(
        av_api_key=av_api_key,
        alpaca_api_key_id=alpaca_api_key_id,
        alpaca_secret_key=alpaca_secret_key
    )

    crypto_api = CryptoAPI(
        alpaca_api_key_id=alpaca_api_key_id,
        alpaca_secret_key=alpaca_secret_key
    )

    instruments = session.query(Instrument) \
        .filter(
            or_(
                Instrument.status == 'active',
                Instrument.status == 'prerelease',
            )
         ) \
        .all()

    for instrument in instruments:
        if instrument.symbol not in selected_instruments and len(selected_instruments) > 0:
            continue
        print(f'Ticker: {instrument.symbol}')

        try:

            if instrument.type == 'stock':
                price_history_bars = stock_api.get_stock_price_history(instrument.symbol)
            elif instrument.type == 'crypto':
                price_history_bars = crypto_api.get_crypto_price_history(symbol=instrument.symbol)
            
            for bar in price_history_bars:
                session.merge(InstrumentKPI_PriceHistory(
                    instrument_id=instrument.id,
                    timeframe="1DAY",
                    date_as_of=rfc3339_to_datetime(bar['t']),
                    price_open=bar['o'],
                    price_high=bar['h'],
                    price_low=bar['l'],
                    price_close=bar['c'],
                    transaction_volume=bar['v'],
                    date_last_updated=func.now()
                ))

            session.commit()

        except Exception as e:
            print(e)
    session.close()


@click.command()
@click.option('--db-host', required=True, default=os.getenv('APP_DB_HOST', ''))
@click.option('--db-port', required=True, default=os.getenv('APP_DB_PORT', ''))
@click.option('--db-user', required=True, default=os.getenv('APP_DB_USER', ''))
@click.option('--db-pass', required=True, default=os.getenv('APP_DB_PASSWORD', ''))
@click.option('--db-name', required=True, default=os.getenv('APP_DB_NAME', ''))
@click.option('--av-api_key', required=True, default= os.getenv('ALPHAVANTAGE_API_KEY', ''))
@click.option('--alpaca-api_key_id', required=True, default=os.getenv('ALPACA_API_KEY_ID', ''))
@click.option('--alpaca-secret_key', required=True, default=os.getenv('ALPACA_SECRET_KEY', ''))
def update_kpi(
    db_host: str, db_port: str, db_user: str, db_pass: str, db_name: str,
    av_api_key: str, alpaca_api_key_id: str, alpaca_secret_key: str) -> None:
    """
    Update the KPI for all instruments.
    """

    session = create_session(db_host=db_host, db_port=db_port, db_user=db_user, db_pass=db_pass, db_name=db_name)

    stock_api = StockAPI(
        av_api_key=av_api_key,
        alpaca_api_key_id=alpaca_api_key_id,
        alpaca_secret_key=alpaca_secret_key)

    instruments = session.query(Instrument) \
        .filter(
            or_(
                Instrument.status == 'active',
                Instrument.status == 'prerelease',
            )
         ) \
        .filter(
            Instrument.type == 'stock'
        ) \
        .all()

    for instrument in instruments:
        if instrument.symbol not in selected_instruments and len(selected_instruments) > 0:
            continue
        print(f'Ticker: {instrument.symbol}')
        try:
            kpi_eps_fq, kpi_eps_fy = stock_api.get_stock_eps(instrument.symbol)
            print('Latest EPS:', kpi_eps_fq[0], kpi_eps_fy[0])
            kpi_balance_sheet_reports = stock_api.get_stock_balance_sheet(instrument.symbol)
            print('A&L reports:', len(kpi_balance_sheet_reports))
            
            """
            `date_last_updated=func.now()` forces SQLAlchemy
            to make changes to the database even if the indicators remain the same.
            We should always keep track of the last updates so that it could be
            accurately displayed in the app UI.
            """

            # EPS per fiscal quarter
            for quarter in kpi_eps_fq:
                session.merge(StockKPI_EPS_FQ(
                    instrument_id=instrument.id,
                    date_fiscal_ending=quarter['date_fiscal_ending'],
                    date_reported=quarter['date_reported'],
                    reported_eps=quarter['reported_eps'],
                    consensus_eps=quarter['consensus_eps'],
                    surprise_abs=quarter['surprise_abs'],
                    surprise_perc=quarter['surprise_perc'],
                    date_last_updated=func.now()
                ))

            session.commit()

            # EPS per fiscal year
            for year in kpi_eps_fy:
                session.merge(StockKPI_EPS_FY(
                    instrument_id=instrument.id,
                    date_fiscal_ending=year['date_fiscal_ending'],
                    reported_eps=year['reported_eps'],
                    date_last_updated=func.now()
                ))

            session.commit()
            
            # Balance sheet reports
            for balance_sheet in kpi_balance_sheet_reports:
                session.merge(StockKPI_BalanceSheet(
                    instrument_id=instrument.id,
                    date_last_updated=func.now(),
                    **balance_sheet
                ))

            session.commit()

        except Exception as e:
            print(e)
            
    session.close()

@click.command()
@click.option('--db-host', required=True, default=os.getenv('APP_DB_HOST', ''))
@click.option('--db-port', required=True, default=os.getenv('APP_DB_PORT', ''))
@click.option('--db-user', required=True, default=os.getenv('APP_DB_USER', ''))
@click.option('--db-pass', required=True, default=os.getenv('APP_DB_PASSWORD', ''))
@click.option('--db-name', required=True, default=os.getenv('APP_DB_NAME', ''))
def process_kpi(db_host: str, db_port: str, db_user: str, db_pass: str, db_name: str,) -> None:
    # process EPS
    session = create_session(db_host=db_host, db_port=db_port, db_user=db_user, db_pass=db_pass, db_name=db_name)
    instruments = session.query(Instrument) \
        .filter(
            or_(
                Instrument.status == 'active',
                Instrument.status == 'prerelease',
            )
         ) \
        .filter(
            Instrument.type == 'stock'
        ) \
        .all()
    for instrument in instruments:
        if instrument.symbol not in selected_instruments and len(selected_instruments) > 0:
            continue
        try:
            kpi_eps_fq = session.query(StockKPI_EPS_FQ).filter(
                StockKPI_EPS_FQ.instrument_id == instrument.id).order_by(StockKPI_EPS_FQ.date_fiscal_ending.desc()).all()
            kpi_eps_fy = session.query(StockKPI_EPS_FY).filter(
                StockKPI_EPS_FY.instrument_id == instrument.id).order_by(StockKPI_EPS_FY.date_fiscal_ending.desc()).all()

            # remove all existing summary metrics related to EPS
            session.query(InstrumentKPI_Summary).filter(
                InstrumentKPI_Summary.instrument_id == instrument.id,
                InstrumentKPI_Summary.category == 'EPS'
            ).delete()

            if len(kpi_eps_fq) >=2:
                fq_sequence = [ report.reported_eps for report in kpi_eps_fq if type(report.reported_eps) is float ]
                growth_meter_q = get_recent_growth_pattern(sequence=fq_sequence)
                profitability_meter_q = get_recent_positive_pattern(sequence=fq_sequence)

                # Quarterly earnings - growth
                session.merge(InstrumentKPI_Summary(
                    instrument_id=instrument.id,
                    category='EPS',
                    fiscal='quarter',
                    kpi_key='GROWTH',
                    kpi_value=str(growth_meter_q),
                    date_as_of=kpi_eps_fq[0].date_fiscal_ending,
                    date_last_updated=func.now()
                ))
                
                # Quarterly earnings - profitability
                session.merge(InstrumentKPI_Summary(
                    instrument_id=instrument.id,
                    category='EPS',
                    fiscal='quarter',
                    kpi_key='PROFIT',
                    kpi_value=str(profitability_meter_q),
                    date_as_of=kpi_eps_fq[0].date_fiscal_ending,
                    date_last_updated=func.now()
                ))
            else:
                growth_meter_q = None
                profitability_meter_q = None

                # Report insufficient data
                session.merge(InstrumentKPI_Summary(
                    instrument_id=instrument.id,
                    category='EPS',
                    fiscal='quarter',
                    kpi_key='INSUFFICIENT_DATA',
                    kpi_value="No data",
                    date_as_of=func.now(),
                    date_last_updated=func.now()
                ))

            if len(kpi_eps_fy) >=2:
                fy_sequence = [report.reported_eps for report in kpi_eps_fy if type(report.reported_eps) is float ]
                growth_meter_y = get_recent_growth_pattern(sequence=fy_sequence)
                profitability_meter_y = get_recent_positive_pattern(sequence=fy_sequence)

                # Annual earnings - growth
                session.merge(InstrumentKPI_Summary(
                    instrument_id=instrument.id,
                    category='EPS',
                    fiscal='year',
                    kpi_key='GROWTH',
                    kpi_value=str(growth_meter_y),
                    date_as_of=kpi_eps_fq[0].date_fiscal_ending,
                    date_last_updated=func.now()
                ))
                
                # Annual earnings - profitability
                session.merge(InstrumentKPI_Summary(
                    instrument_id=instrument.id,
                    category='EPS',
                    fiscal='year',
                    kpi_key='PROFIT',
                    kpi_value=str(profitability_meter_y),
                    date_as_of=kpi_eps_fy[0].date_fiscal_ending,
                    date_last_updated=func.now()
                ))

            else:
                growth_meter_y = None
                profitability_meter_y = None

                # Report insufficient data
                session.merge(InstrumentKPI_Summary(
                    instrument_id=instrument.id,
                    category='EPS',
                    fiscal='year',
                    kpi_key='INSUFFICIENT_DATA',
                    kpi_value="No data",
                    date_as_of=func.now(),
                    date_last_updated=func.now()
                ))

            session.commit()

        except SQLAlchemyError as e:
            print(e)
            session.rollback()


# @click.command()
# @click.option('--db-host', required=True, default=os.getenv('APP_DB_HOST', ''))
# @click.option('--db-port', required=True, default=os.getenv('APP_DB_PORT', ''))
# @click.option('--db-user', required=True, default=os.getenv('APP_DB_USER', ''))
# @click.option('--db-pass', required=True, default=os.getenv('APP_DB_PASSWORD', ''))
# @click.option('--db-name', required=True, default=os.getenv('APP_DB_NAME', ''))
# def refresh_portfolios(db_host: str, db_port: str, db_user: str, db_pass: str, db_name: str,) -> None:

 
cli.add_command(list_available_crypto_assets)
cli.add_command(update_latest_price)
cli.add_command(update_kpi)
cli.add_command(process_kpi)
cli.add_command(update_price_history)


if __name__ == '__main__':
    cli()
