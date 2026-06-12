import os
import pytest

# Must be set before any app module is imported during test collection.
# APP_ENV=development disables the HTTPS-only cookie flag so the HTTP test
# client can send cookies, and also skips the CORS_ALLOWED_ORIGINS requirement.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-minimum-64-characters-padded-here-abcdef!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_ENV", "development")


@pytest.fixture(autouse=True)
def enable_registration(monkeypatch):
    """Enable /register for all tests. Tests that need it disabled can call
    monkeypatch.delenv('ALLOW_REGISTRATION', raising=False) in the test body."""
    monkeypatch.setenv("ALLOW_REGISTRATION", "true")


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset in-memory rate limiter storage between tests so limits don't accumulate."""
    from app.rate_limiter import limiter
    yield
    limiter._storage.reset()
