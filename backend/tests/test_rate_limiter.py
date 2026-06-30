import ipaddress
import pytest
from unittest.mock import MagicMock
import app.rate_limiter as rl


def _make_request(remote_addr: str, xff: str | None = None) -> MagicMock:
    req = MagicMock()
    req.client.host = remote_addr
    req.headers = {}
    if xff is not None:
        req.headers = {"X-Forwarded-For": xff}
    # slowapi's get_remote_address reads request.client.host
    return req


def test_is_trusted_proxy_invalid_ip_returns_false():
    assert rl._is_trusted_proxy("not-an-ip") is False


def test_get_real_ip_untrusted_direct_returns_remote():
    # No trusted proxies configured → always return direct IP
    original_nets = rl._trusted_proxy_nets[:]
    original_proxies = rl._trusted_proxies.copy()
    rl._trusted_proxy_nets.clear()
    rl._trusted_proxies.clear()
    try:
        req = _make_request("1.2.3.4", xff="10.0.0.1")
        assert rl.get_real_ip(req) == "1.2.3.4"
    finally:
        rl._trusted_proxy_nets.extend(original_nets)
        rl._trusted_proxies.update(original_proxies)


def test_get_real_ip_trusted_proxy_reads_xff():
    original_nets = rl._trusted_proxy_nets[:]
    original_proxies = rl._trusted_proxies.copy()
    rl._trusted_proxy_nets.clear()
    rl._trusted_proxies.clear()
    rl._trusted_proxies.add("10.0.0.2")
    try:
        req = _make_request("10.0.0.2", xff="203.0.113.5, 10.0.0.2")
        # 203.0.113.5 is not trusted → returned as real client
        assert rl.get_real_ip(req) == "203.0.113.5"
    finally:
        rl._trusted_proxy_nets.clear()
        rl._trusted_proxies.clear()
        rl._trusted_proxy_nets.extend(original_nets)
        rl._trusted_proxies.update(original_proxies)


def test_get_real_ip_all_xff_trusted_returns_first():
    original_nets = rl._trusted_proxy_nets[:]
    original_proxies = rl._trusted_proxies.copy()
    rl._trusted_proxy_nets.clear()
    rl._trusted_proxies.clear()
    rl._trusted_proxies.update({"10.0.0.1", "10.0.0.2"})
    try:
        req = _make_request("10.0.0.2", xff="10.0.0.1, 10.0.0.2")
        assert rl.get_real_ip(req) == "10.0.0.1"
    finally:
        rl._trusted_proxy_nets.clear()
        rl._trusted_proxies.clear()
        rl._trusted_proxy_nets.extend(original_nets)
        rl._trusted_proxies.update(original_proxies)


def test_get_real_ip_trusted_proxy_no_xff_returns_direct():
    original_nets = rl._trusted_proxy_nets[:]
    original_proxies = rl._trusted_proxies.copy()
    rl._trusted_proxy_nets.clear()
    rl._trusted_proxies.clear()
    rl._trusted_proxies.add("10.0.0.1")
    try:
        req = _make_request("10.0.0.1", xff=None)
        assert rl.get_real_ip(req) == "10.0.0.1"
    finally:
        rl._trusted_proxy_nets.clear()
        rl._trusted_proxies.clear()
        rl._trusted_proxy_nets.extend(original_nets)
        rl._trusted_proxies.update(original_proxies)
