#!/bin/bash

. .env

# Add new tokens from "Solana Ecosystem" list on CMC if there are any
python -m app.analytics.new_main add-solana-tokens
python -m app.analytics.new_main update-price-history --timeframe '1D'