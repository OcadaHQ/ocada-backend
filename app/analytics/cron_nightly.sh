#!/bin/bash
# daily updates: price history etc.

. .env

# ingest latest pricing data
python -m app.analytics.main update-price-history
