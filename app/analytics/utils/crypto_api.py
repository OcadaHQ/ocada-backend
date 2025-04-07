from datetime import datetime, timedelta
from pickletools import anyobject
from typing import Tuple
import requests

from app.analytics.utils.errors import AlphavantageRateLimitError


class CryptoAPI:
    
    def __init__(self,
        alpaca_api_key_id: str,
        alpaca_secret_key: str):

        # alpaca config
        self._alpaca_base_url = 'https://data.alpaca.markets/v1beta3/crypto'
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

    # get crypto price using Alpaca API
    def get_latest_crypto_price(self, symbol: str):
        """
        Get the latest crypto price for a given symbol
        """

        alpaca_symbol = f"{symbol}/USD"
        headers = {
            'APCA-API-KEY-ID': self._alpaca_api_key_id,
            'APCA-API-SECRET-KEY': self._alpaca_secret_key
        }
        params = {
            "symbols": alpaca_symbol
        }

        url = f'{self._alpaca_base_url}/us/latest/trades'
        response = requests.get(url=url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f'Error getting latest crypto price for {alpaca_symbol}, status code {response.status_code} {response.text}')
        else:
            r = response.json()
            if r.get('trades', {}).get(alpaca_symbol, None) is not None:
                date_as_of = self.alpaca_date_to_datetime(r['trades'][alpaca_symbol]['t'])
                return {
                    'as_of': date_as_of,
                    'price': self._is_like_float(r['trades'][alpaca_symbol]['p'])
                }
        return None

    # get crypto price using Alpaca API
    def get_crypto_price_history(self, symbol: str):
        """
        Get price history for a given crypto symbol (e.g. BTC/USD)
        """

        alpaca_symbol = f"{symbol}/USD"
        headers = {
            'APCA-API-KEY-ID': self._alpaca_api_key_id,
            'APCA-API-SECRET-KEY': self._alpaca_secret_key
        } 

        days = 366
        # datetime one year ago
        date_one_year_ago = datetime.now() - timedelta(days=days)
        # format date in rfc 3339
        date_one_year_ago_str = date_one_year_ago.strftime('%Y-%m-%d')

        url = f'{self._alpaca_base_url}/us/bars'
        params = {
            "symbols": alpaca_symbol,
            "start": date_one_year_ago_str,
            "timeframe": "1Day",
            "limit": days
        }

        response = requests.get(url=url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f'Error getting price history for {alpaca_symbol}')
        else:
            r = response.json()
            if r.get('bars', None) is not None:
                return r['bars'][alpaca_symbol]

        return None

    def get_crypto_assets(self):
        """
        Get available crypto assets
        """

        headers = {
            'APCA-API-KEY-ID': self._alpaca_api_key_id,
            'APCA-API-SECRET-KEY': self._alpaca_secret_key
        }
        url = f'https://api.alpaca.markets/v2/assets?asset_class=crypto'
        response = requests.get(url=url, headers=headers)
        return response.json()