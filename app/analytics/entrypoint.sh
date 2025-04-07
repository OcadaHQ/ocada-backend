#!/bin/bash

# create .env file and populate it with environment variables

rm -f .env
touch .env
env | while IFS= read -r line; do
    value=${line#*=}
    name=${line%%=*}
    echo "export $name=$value" >> .env
done

# start cron
service cron restart

# Keep alive
tail -f /dev/null
