#!/bin/bash

# create .env file and populate it with environment variables

rm -f /app/.env
touch /app/.env
env | while IFS= read -r line; do
    value=${line#*=}
    name=${line%%=*}
    echo "export $name=$value" >> /app/.env
done

# start cron
echo "entrypoint: start cron"
service cron restart

# adhoc xp recalculation
# echo "entrypoint: run tools.xp_onrestart_recalc"
# python -m app.api.tools.xp_onrestart_recalc

# run the web server
echo "entrypoint: start webserver"
uvicorn app.api.main:app --root-path /api --host 0.0.0.0 --port 80
