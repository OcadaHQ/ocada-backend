import json
import requests
import os

from typing import List, Dict, Any, Optional, Generator
from app.analytics.utils.helpers import chunk_list, get_dict_by_id

CMC_API_KEY = os.getenv("CMC_API_KEY")

cmc_headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': CMC_API_KEY,
}

base_api_url = 'https://pro-api.coinmarketcap.com/'

def coinmarketcap_api_call(url: str, params: Dict[str, Any], headers: Dict[str, str] = cmc_headers) -> Any:
    """Make a GET request to the CoinMarketCap API."""
    full_url = base_api_url + url
    try:
        response = requests.get(full_url, headers=headers, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses

        data = response.json()
        return data
    except requests.RequestException as e:
        raise Exception(f"Error calling CoinMarketCap API: {response.text}")

def get_tokens_by_category_name(cat_name: str) -> Dict[str, Any]:
    """Get tokens by category name from CoinMarketCap."""
    # Get all categories
    all_categories = coinmarketcap_api_call(
        'v1/cryptocurrency/categories',
        {'start': '1', 'limit': '5000'}
    )

    # Find category ID
    res = [x for x in all_categories['data'] if cat_name in x['name']]
    if len(res):
        cat_id = res[0]['id']
    else:
        raise Exception("Error fetching category ID")

    # Get all tokens for the category
    category_tokens = coinmarketcap_api_call(
        'v1/cryptocurrency/category',
        {'start': '1', 'limit': '1000', 'id': cat_id}
    )
    return category_tokens

def get_token_metadata_by_id(ids: str) -> Dict[str, Any]:
    """Get token metadata by ID from CoinMarketCap."""
    if isinstance(ids, str):
        ids = ids.split(',')
    token_metadata = {'data': {}}
    for chunk in chunk_list(ids, 100):
        chunk_ids = ','.join(chunk)
        chunk_metadata = coinmarketcap_api_call(
            'v2/cryptocurrency/info',
            {'id': chunk_ids}
        )
        token_metadata['data'].update(chunk_metadata['data'])
    return token_metadata

# Example of token:
# {'id': 28752, 'name': 'dogwifhat', 'symbol': 'WIF', 'slug': 'dogwifhat', 'num_market_pairs': 394, 'date_added': '2023-12-19T09:08:50.000Z', 'tags': ['memes', 'solana-ecosystem', 'doggone-doggerel'], 'max_supply': None, 'circulating_supply': 998905912.903596, 'total_supply': 998905912.903596, 'platform': {'id': 5426, 'name': 'Solana', 'symbol': 'SOL', 'slug': 'solana', 'token_address': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm'}, 'is_active': 1, 'infinite_supply': False, 'cmc_rank': 41, 'is_fiat': 0, 'self_reported_circulating_supply': None, 'self_reported_market_cap': None, 'tvl_ratio': None, 'last_updated': '2024-06-10T11:46:00.000Z', 'quote': {'USD': {'price': 2.7343247336712606, 'volume_24h': 392915353.44112575, 'volume_change_24h': 3.1483, 'percent_change_1h': -0.49028537, 'percent_change_24h': 0.9489466, 'percent_change_7d': -20.59756681, 'percent_change_30d': -9.73873009, 'percent_change_60d': -23.84629692, 'percent_change_90d': 40.63046784, 'market_cap': 2731333144.2627726, 'market_cap_dominance': 0.1079, 'fully_diluted_market_cap': 2731333144.26, 'tvl': None, 'last_updated': '2024-06-10T11:46:00.000Z'}}}
def get_solana_tokens() -> List[Dict[str, Any]]:
    """Get active tokens in the Solana ecosystem from CoinMarketCap."""
    solana_ecosystem_tokens = get_tokens_by_category_name('Solana Ecosystem')
    # Get tokens that belong to Solana chain and are active
    solana_tokens = [t for t in solana_ecosystem_tokens['data']['coins'] if t['platform'] and t['platform']['slug'] == 'solana' and t['is_active']]
    return solana_tokens

# THIS METHOD IS NOT NEED WHILE WE ARE USING PAID BIRDEYE API
# def get_tokens_for_onboarding(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """Create a data structure for onboarding new tokens into the app using CMC."""
#     new_tokens = []
#     token_ids = [t['id'] for t in tokens]
#     ids = ','.join(map(str, token_ids))
#     tokens_metadata = get_token_metadata_by_id(ids)
#     for token_id in token_ids:
#         data = get_dict_by_id(tokens, token_id)
#         metadata = tokens_metadata['data'][str(token_id)]
#         instrument_dict = {
#             token_id: {
#                 'cmc_id': f"cmc_{token_id}",
#                 'name': metadata.get('name'),
#                 'symbol': metadata.get('symbol'),
#                 'tags': ', '.join(tag.lower() for tag in metadata.get('tag-names', [])),
#                 'subtitle': metadata.get('description'),
#                 'type': 'crypto',
#                 'image_url': metadata.get('logo'),
#                 'is_well_known': 0,
#                 'status': 'active',
#                 'token_address': metadata.get('contract_address', [{}])[0].get('contract_address') if metadata.get('contract_address') else None,
#                 'chain': metadata.get('platform', {}).get('name', '').lower() if metadata.get('platform') else None,
#                 'twitter_url': metadata.get('urls', {}).get('twitter', [None])[0],
#                 'website_url': metadata.get('urls', {}).get('website', [None])[0],
#                 'tg_url': metadata.get('urls', {}).get('chat', [None])[0],
#                 'explorer_url': metadata.get('urls', {}).get('explorer', [None])[0]
#             }
#         }
#         new_tokens.append(instrument_dict)
#     return new_tokens

if __name__ == "__main__":
    try:
        solana_tokens = get_solana_tokens()
        # tokens = get_tokens_for_onboarding(solana_tokens)
        print(json.dumps(solana_tokens, indent=4))
    except Exception as e:
        print(f"Error: {e}")
