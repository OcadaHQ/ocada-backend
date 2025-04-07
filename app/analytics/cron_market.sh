#!/bin/bash
# frequent update of market data: pricing etc.
# runs every 5 minutes

. .env

# ingest and update latest pricing data
python -m app.analytics.main update-latest-price
