import os

SECRET_KEY = os.environ["SECRET_KEY"]  # KeyError if missing — intentional
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
DATABASE_URL: str = os.environ["DATABASE_URL"]

_APP_ENV = os.getenv("APP_ENV", "production").lower()
if DATABASE_URL.startswith("sqlite") and _APP_ENV not in {"development", "dev", "test", "testing"}:
    raise ValueError(
        "SQLite is not allowed outside development. "
        "Set DATABASE_URL to a PostgreSQL connection string, "
        "or set APP_ENV=development to allow SQLite locally."
    )
