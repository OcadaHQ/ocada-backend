# Data models

* ORM models in `models.py` (SQLalchemy)
* API schema in `api_schema.py` (Pydantic)

# Alembic migrations

Generate a revision:

```shell
alembic revision --autogenerate -m "My comment"
```

Upgrade the DB to latest version:

```shell
alembic upgrade head
```

