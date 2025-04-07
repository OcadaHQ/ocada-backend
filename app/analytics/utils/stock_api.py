from datetime import datetime, timedelta
from pickletools import anyobject
from typing import Tuple
import requests
from retry import retry

from app.analytics.utils.errors import AlphavantageRateLimitError


class StockAPI:
    
    def __init__(self,
        av_api_key: str,
        alpaca_api_key_id: str,
        alpaca_secret_key: str):
        # alphavantage config
        self._av_base_url = 'https://www.alphavantage.co/query'
        self._av_api_key = av_api_key

        # alpaca config
        self._alpaca_base_url = 'https://data.alpaca.markets/v2'
        self._alpaca_api_key_id = alpaca_api_key_id
        self._alpaca_secret_key = alpaca_secret_key

    @staticmethod
    def _is_like_float(string: str):
        try:
            float(string)
            return float(string)
        except ValueError:
            return None

    @staticmethod
    def alpaca_date_to_datetime(raw_date: str) -> datetime:
        date_format = '%Y-%m-%dT%H:%M:%S%z'
        date_split = raw_date.split('.')
        date_str = date_split[0] + 'Z'

        return datetime.strptime(date_str, date_format)

    # get stock price using Alpaca API
    def get_latest_stock_price(self, symbol: str):
        """
        Get the latest stock price for the given stock symbol
        """

        headers = {
            'APCA-API-KEY-ID': self._alpaca_api_key_id,
            'APCA-API-SECRET-KEY': self._alpaca_secret_key
        }

        url = f'{self._alpaca_base_url}' \
            f'/stocks/{symbol}/trades/latest'
        response = requests.get(url=url, headers=headers)
        if response.status_code != 200:
            raise Exception(f'Error getting latest stock price for {symbol}')
        else:
            r = response.json()
            if r.get('trade', None) is not None:
                date_as_of = self.alpaca_date_to_datetime(r['trade']['t'])
                return {
                    'as_of': date_as_of,
                    'price': self._is_like_float(r['trade']['p'])
                }
        return None

    # get stock price using Alpaca API
    def get_stock_price_history(self, symbol: str):
        """
        Get the latest stock price for the given stock symbol
        """

        headers = {
            'APCA-API-KEY-ID': self._alpaca_api_key_id,
            'APCA-API-SECRET-KEY': self._alpaca_secret_key
        } 

        days = 366
        # datetime one year ago
        date_one_year_ago = datetime.now() - timedelta(days=days)
        # format date in rfc 3339
        date_one_year_ago_str = date_one_year_ago.strftime('%Y-%m-%d')

        url = f'{self._alpaca_base_url}' \
            f'/stocks/{symbol}/bars?' \
            f'start={date_one_year_ago_str}&' \
            f'timeframe=1Day&' \
            f'adjustment=split&' \
            f'limit={days}'

        response = requests.get(url=url, headers=headers)
        if response.status_code != 200:
            raise Exception(f'Error getting price history for {symbol}')
        else:
            r = response.json()
            if r.get('bars', None) is not None:
                return r['bars']

        return None

    @retry(AlphavantageRateLimitError, tries=-1, delay=5)
    def get_stock_eps(self, symbol: str) -> anyobject:
        """
        Get the latest EPS for the given stock symbol
        """
        url = f'{self._av_base_url}?' \
            f'function=EARNINGS&' \
            f'symbol={symbol}&' \
            f'apikey={self._av_api_key}'

        response = requests.get(url)

        if response.status_code != 200:
            raise AlphavantageRateLimitError(f'HTTP code {response.status_code}')
        elif 'frequency' in response.json().get('Note', ''):
            raise AlphavantageRateLimitError(f'{symbol}/EPS: Rate limit exceeded')
        else:
            data = response.json()
            quarterly_eps = []
            annual_eps = []

            # process quarterly EPS
            for quarter in data['quarterlyEarnings']:
                quarterly_eps.append({
                    'date_fiscal_ending': datetime.strptime(quarter['fiscalDateEnding'], '%Y-%m-%d'),
                    'date_reported': datetime.strptime(quarter['reportedDate'], '%Y-%m-%d'),
                    'reported_eps': self._is_like_float(quarter['reportedEPS']),
                    'consensus_eps': self._is_like_float(quarter['estimatedEPS']),
                    'surprise_abs': self._is_like_float(quarter['surprise']),
                    'surprise_perc': self._is_like_float(quarter['surprisePercentage'])
                })

            # process annual EPS
            for year in data['annualEarnings']:
                annual_eps.append({
                    'date_fiscal_ending': datetime.strptime(year['fiscalDateEnding'], '%Y-%m-%d'),
                    'reported_eps': self._is_like_float(year['reportedEPS'])
                })

            return quarterly_eps, annual_eps

    def _create_balance_sheet_object(self, fiscal_period: str, balance_sheet_raw: dict) -> anyobject:
        if fiscal_period not in ['quarter', 'year']:
            raise ValueError(f'Invalid fiscal period {fiscal_period}. \
            Available options: quarter, year')
        
        balance_sheet = {
            'date_fiscal_ending': datetime.strptime(balance_sheet_raw['fiscalDateEnding'], '%Y-%m-%d'),
            'fiscal_period': fiscal_period,
            'reported_currency': balance_sheet_raw['reportedCurrency'],
            'total_assets': self._is_like_float(balance_sheet_raw['totalAssets']),
            'current_assets': self._is_like_float(balance_sheet_raw['totalCurrentAssets']),
            'cce': self._is_like_float(balance_sheet_raw['cashAndCashEquivalentsAtCarryingValue']),
            'cash_and_short_term_investments': self._is_like_float(balance_sheet_raw['cashAndShortTermInvestments']),
            'inventory': self._is_like_float(balance_sheet_raw['inventory']),
            'current_net_receivables': self._is_like_float(balance_sheet_raw['currentNetReceivables']),
            'other_current_assets': self._is_like_float(balance_sheet_raw['otherCurrentAssets']),
            'noncurrent_assets': self._is_like_float(balance_sheet_raw['totalNonCurrentAssets']),
            'ppe': self._is_like_float(balance_sheet_raw['propertyPlantEquipment']),
            'accumulated_depreciation_amortization_ppe': self._is_like_float(balance_sheet_raw['accumulatedDepreciationAmortizationPPE']),
            'intangible_assets': self._is_like_float(balance_sheet_raw['intangibleAssets']),
            'intangible_assets_excluding_goodwill': self._is_like_float(balance_sheet_raw['intangibleAssetsExcludingGoodwill']),
            'goodwill': self._is_like_float(balance_sheet_raw['goodwill']),
            'total_investments': self._is_like_float(balance_sheet_raw['investments']),
            'long_term_investments': self._is_like_float(balance_sheet_raw['longTermInvestments']),
            'short_term_investments': self._is_like_float(balance_sheet_raw['shortTermInvestments']),
            'other_noncurrent_assets': self._is_like_float(balance_sheet_raw['otherNonCurrentAssets']),
            'total_liabilities': self._is_like_float(balance_sheet_raw['totalLiabilities']),
            'current_liabilities': self._is_like_float(balance_sheet_raw['totalCurrentLiabilities']),
            'current_accounts_payable': self._is_like_float(balance_sheet_raw['currentAccountsPayable']),
            'deferred_revenue': self._is_like_float(balance_sheet_raw['deferredRevenue']),
            'current_debt': self._is_like_float(balance_sheet_raw['currentDebt']),
            'short_term_debt': self._is_like_float(balance_sheet_raw['shortTermDebt']),
            'other_current_liabilities': self._is_like_float(balance_sheet_raw['otherCurrentLiabilities']),
            'noncurrent_liabilities': self._is_like_float(balance_sheet_raw['totalNonCurrentLiabilities']),
            'capital_lease_obligations': self._is_like_float(balance_sheet_raw['capitalLeaseObligations']),
            'long_term_debt': self._is_like_float(balance_sheet_raw['longTermDebt']),
            'current_long_term_debt': self._is_like_float(balance_sheet_raw['currentLongTermDebt']),
            'noncurrent_long_term_debt': self._is_like_float(balance_sheet_raw['longTermDebtNoncurrent']),
            'short_long_term_debt': self._is_like_float(balance_sheet_raw['shortLongTermDebtTotal']),
            'other_noncurrent_liabilities': self._is_like_float(balance_sheet_raw['otherNonCurrentLiabilities']),
            'total_sharteholders_equity': self._is_like_float(balance_sheet_raw['totalShareholderEquity']),
            'treasury_stock': self._is_like_float(balance_sheet_raw['treasuryStock']),
            'retained_earnings': self._is_like_float(balance_sheet_raw['retainedEarnings']),
            'common_stock': self._is_like_float(balance_sheet_raw['commonStock']),
            'common_stock_outstanding': self._is_like_float(balance_sheet_raw['commonStockSharesOutstanding']),
        }

        return balance_sheet

    @retry(AlphavantageRateLimitError, tries=-1, delay=5)
    def get_stock_balance_sheet(self, symbol: str) -> anyobject:
        """
        Get the latest balance sheet (assets and liabilities) for the given stock symbol
        """

        url = f'{self._av_base_url}?' \
            f'function=BALANCE_SHEET&' \
            f'symbol={symbol}&' \
            f'apikey={self._av_api_key}'

        response = requests.get(url)

        if response.status_code != 200:
            raise AlphavantageRateLimitError(f'HTTP code {response.status_code}')
        elif 'frequency' in response.json().get('Note', ''):
            raise AlphavantageRateLimitError(f'{symbol}/balance sheet: Rate limit exceeded')
        else:
            data = response.json()

            balance_sheet_reports = []

            for report in data['quarterlyReports']:
                balance_sheet_reports.append(
                    self._create_balance_sheet_object(
                        fiscal_period='quarter',
                        balance_sheet_raw=report
                    )
                )

            for report in data['annualReports']:
                balance_sheet_reports.append(
                    self._create_balance_sheet_object(
                        fiscal_period='year',
                        balance_sheet_raw=report
                    )
                )

            return balance_sheet_reports
