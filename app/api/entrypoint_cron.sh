#!/bin/bash

# create .env file and populate it with environment variables
rm -f /app/.env
touch /app/.env
env | while IFS= read -r line; do
    value=${line#*=}
    name=${line%%=*}
    echo "export $name=$value" >> /app/.env
done
