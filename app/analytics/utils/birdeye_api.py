import json
import requests
import os
from datetime import datetime, timedelta

from typing import List, Dict, Any, Optional
from app.analytics.utils.helpers import chunk_list



BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

birdeye_headers = {
    'Accepts': 'application/json',
    'X-API-KEY': BIRDEYE_API_KEY,
}

base_api_url = 'https://public-api.birdeye.so/defi/'

def birdeye_api_call(url: str, headers: Dict[str, str] = birdeye_headers, 
                     get_params: Optional[str] = None, post_params: Optional[Dict[str, Any]] = None) -> Any:
    """Make a GET or POST request to the Bird Eye API."""
    full_url = base_api_url + url
    try:
        if get_params:
            response = requests.get(full_url, params=get_params, headers=headers)
        elif post_params:
            response = requests.post(full_url, json=post_params, headers={**headers, "content-type": "application/json"})
        else:
            raise ValueError("Either get_params or post_params must be provided")
        response.raise_for_status()  # Raise HTTPError for bad responses
        resp = response.json()
        if resp.get('success'):
            return resp.get('data')
        else:
            raise Exception(f"Error calling Bird Eye API (2): {response.text}")
    except requests.RequestException as e:
        raise Exception(f"Error calling Bird Eye API: {str(e)}")

def get_token_overview_by_address(address: str) -> Dict[str, Any]:
    """Get the token overview for a specific address."""
    params = {'address': address}
    token_data = birdeye_api_call('token_overview', get_params=params)
    return token_data

def get_latest_crypto_price(addresses: List[str]) -> Dict[str, Any]:
    """Get the prices of multiple tokens."""
    chunk_size = 100  # Adjust chunk size as needed
    all_prices = {}
    for chunk in chunk_list(addresses, chunk_size):
        post_params = {'list_address': ','.join(chunk)}
        chunk_prices = birdeye_api_call('multi_price', post_params=post_params)
        all_prices.update(chunk_prices)
    return all_prices

def get_crypto_price_history(address, timeframe='1D', last_fetched_timestamp=None):
    if timeframe in ['1D', '3D', '1W', '1M']:
        days = 366
    elif timeframe in ['1m', '3m', '5m']:
        days = 2
    else:
        days = 10

    if last_fetched_timestamp:
        time_from = last_fetched_timestamp
    else:
        time_from = int((datetime.now() - timedelta(days=days)).timestamp())

    params = {
        'address': address,
        'type': timeframe,
        'time_from': time_from,
        'time_to': int(datetime.now().timestamp())
    }
    prices = birdeye_api_call('ohlcv', get_params=params)
    return prices

def get_risk_score(address):
    resp = requests.get(f'https://api.rugcheck.xyz/v1/tokens/{address}/report/summary')
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    # Example usage:
    try:
        address = 'example_token_address'
        overview = get_token_overview_by_address(address)
        print(json.dumps(overview, indent=4))

        addresses = ['address1', 'address2', 'address3']
        prices = get_latest_crypto_price(addresses)
        print(json.dumps(prices, indent=4))
    except Exception as e:
        print(f"Error: {e}")