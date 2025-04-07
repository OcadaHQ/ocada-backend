#!/bin/bash
# frequent portfolio refresh
# runs every 5 minutes

#. /app/.env

# ingest and update latest pricing data
python -m app.api.tools.portfolio_refresh
