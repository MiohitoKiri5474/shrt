import pytest


@pytest.fixture(autouse=True)
def enable_registration(monkeypatch):
    """Enable /register for all tests. Tests that need it disabled can call
    monkeypatch.delenv('ALLOW_REGISTRATION', raising=False) in the test body."""
    monkeypatch.setenv("ALLOW_REGISTRATION", "true")
