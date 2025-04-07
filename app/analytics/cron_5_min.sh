#!/bin/bash

. .env

python -m app.analytics.new_main update-price-history --timeframe '5m'
