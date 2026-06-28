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

_REDIS_URL = os.getenv("REDIS_URL", "")
if _APP_ENV not in {"development", "dev", "test", "testing"} and "changeme" in _REDIS_URL:
    raise ValueError(
        "REDIS_URL contains the default password 'changeme'. "
        "Set REDIS_PASSWORD to a strong value with: openssl rand -hex 32"
    )
# Fail fast in production when REDIS_URL is absent. Without Redis, rate limiting
# falls back to in-memory (not shared across workers) and JWT revocation via
# token blocklist is silently disabled, leaving logged-out tokens valid.
if _APP_ENV not in {"development", "dev"} and not _REDIS_URL:
    raise ValueError(
        "REDIS_URL must be set in production "
        "(required for rate limiting and token revocation)"
    )
