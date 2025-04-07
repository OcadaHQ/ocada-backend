#!/bin/bash
# update is_premium on the user model
# runs every 3 hours

#. /app/.env

# ingest and update latest pricing data
python -m app.api.tools.update_premium_status
