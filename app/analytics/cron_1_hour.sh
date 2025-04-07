#!/bin/bash

. .env

python -m app.analytics.new_main update-price-history --timeframe '1H'
python -m app.analytics.new_main update-metrics