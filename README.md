# Development

Set environment to dev to run db locally:

```
export ENVIRONMENT=dev
```

Start the database:

```
docker-compose up database
```

Alternatively prod db could be used (for testing only):

```
export ENVIRONMENT=prod
also export APP_DB_NAME, APP_DB_USER, APP_DB_PORT, APP_DB_PASSWORD and APP_DB_HOST
```

Start the API for local development:

```
uvicorn app.api.main:app --reload --host 0.0.0.0
```

Tear down the database and all containers (useful for changes to the DB models):

```
docker-compose down
```

# Production

Start up production

```
docker-compose up
```

It will launch the database and the backend API.

Redeploy production:

```
sudo docker-compose up --detach --build api
```

# DevOps

Backup the database:

```
sudo docker exec -i backend_database /usr/bin/pg_dump -U snips snips | gzip -9 > postgres-backup-2022_07_24.sql.gz
```

Restore the database

```
pg_restore -U <database_owner> -d <database_name> <path_to_dump>
```