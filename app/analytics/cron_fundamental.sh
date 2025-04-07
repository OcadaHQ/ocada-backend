#!/bin/bash
# infrequent updates of fundamental KPI: balance sheets, etc.
# runs once/twice a day

. .env

# ingest latest fundamental data
python -m app.analytics.main update-kpi

# summarise the KPI data
python -m app.analytics.main process-kpi
