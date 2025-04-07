#!/bin/bash
# run at the very end of the week

#. /app/.env

# ingest and update latest pricing data
python -m app.api.tools.xp_weekly_reset
