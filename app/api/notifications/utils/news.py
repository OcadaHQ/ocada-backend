import os
import requests


def get_latest_news_by_symbol(symbol: str):
    ALPACA_API_KEY_ID = os.getenv("ALPACA_API_KEY_ID")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

    r = requests.get(
        url="https://data.alpaca.markets/v1beta1/news",
        params={
            "sort": "DESC",
            "limit": 10,
            "symbols": [symbol]
        },
        headers={
            "Apca-Api-Key-Id": ALPACA_API_KEY_ID,
            "Apca-Api-Secret-Key": ALPACA_SECRET_KEY
        }
    )
    
    news = r.json().get("news")

    return news


news = get_latest_news_by_symbol(symbol="AMZN")

for piece in news:
    print('source=', piece['source'], ' headline=', piece['headline'])

