import os
from typing import Final

SECRET_KEY = os.environ["SECRET_KEY"]  # KeyError if missing — intentional
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must not be empty")
if len(SECRET_KEY) < 64:
    raise ValueError(
        "SECRET_KEY must be at least 64 characters long. "
        "Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(48))\""
    )
ALGORITHM: Final = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
DATABASE_URL: str = os.environ["DATABASE_URL"]

_APP_ENV = os.getenv("APP_ENV", "production").lower()
if DATABASE_URL.startswith("sqlite") and _APP_ENV not in {"development", "dev", "test", "testing"}:
    raise ValueError(
        "SQLite is not allowed outside development. "
        "Set DATABASE_URL to a PostgreSQL connection string, "
        "or set APP_ENV=development to allow SQLite locally."
    )
