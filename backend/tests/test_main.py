import pytest
from app.main import compute_allowed_hosts


def test_explicit_allowed_hosts_env_wins():
    """ALLOWED_HOSTS, when set, always takes precedence over derivation."""
    result = compute_allowed_hosts("example.com, api.example.com", is_dev=False, cors_origins=["http://other.com"])
    assert result == ["example.com", "api.example.com"]


def test_dev_defaults_to_wildcard_without_env():
    """No ALLOWED_HOSTS in dev must fall back to '*' so local tooling and test
    clients (synthetic Host headers) are never blocked."""
    result = compute_allowed_hosts(None, is_dev=True, cors_origins=["http://localhost:5173"])
    assert result == ["*"]


def test_prod_derives_hosts_from_cors_origins():
    """Without an explicit override, production derives the Host allowlist from
    the already-required CORS origins instead of trusting an unvalidated Host header."""
    result = compute_allowed_hosts(None, is_dev=False, cors_origins=["https://shrt.example.com", "https://admin.example.com"])
    assert result == ["admin.example.com", "shrt.example.com"]


def test_prod_raises_when_no_hosts_derivable():
    """A production deployment with no usable CORS origins must fail fast rather
    than silently allow every Host header."""
    with pytest.raises(ValueError, match="ALLOWED_HOSTS"):
        compute_allowed_hosts(None, is_dev=False, cors_origins=[])
