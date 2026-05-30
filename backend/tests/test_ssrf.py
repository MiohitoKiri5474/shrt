"""Unit tests for validate_no_ssrf — mocks socket.getaddrinfo to avoid live DNS."""
import socket
from unittest.mock import patch

import pytest

from app.schemas import SSRFDNSError, validate_no_ssrf


def _addr(ip: str):
    """Build a minimal getaddrinfo result tuple for a given IP string."""
    return (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))


# ---------------------------------------------------------------------------
# validate_no_ssrf direct tests
# ---------------------------------------------------------------------------

class TestValidateNoSsrf:
    def test_public_ip_allowed(self):
        with patch("socket.getaddrinfo", return_value=[_addr("93.184.216.34")]):
            validate_no_ssrf("http://example.com/")  # must not raise

    def test_private_ip_blocked(self):
        with patch("socket.getaddrinfo", return_value=[_addr("192.168.1.1")]):
            with pytest.raises(ValueError, match="blocked address"):
                validate_no_ssrf("http://internal.example.com/")

    def test_loopback_blocked(self):
        with patch("socket.getaddrinfo", return_value=[_addr("127.0.0.1")]):
            with pytest.raises(ValueError, match="blocked address"):
                validate_no_ssrf("http://localhost/")

    def test_mixed_ips_blocked_if_any_private(self):
        """A hostname resolving to both a public and a private IP must be blocked."""
        results = [_addr("93.184.216.34"), _addr("10.0.0.1")]
        with patch("socket.getaddrinfo", return_value=results):
            with pytest.raises(ValueError, match="blocked address"):
                validate_no_ssrf("http://dual-homed.example.com/")

    def test_link_local_blocked(self):
        with patch("socket.getaddrinfo", return_value=[_addr("169.254.1.1")]):
            with pytest.raises(ValueError, match="blocked address"):
                validate_no_ssrf("http://link-local.example.com/")

    def test_multicast_blocked(self):
        with patch("socket.getaddrinfo", return_value=[_addr("224.0.0.1")]):
            with pytest.raises(ValueError, match="blocked address"):
                validate_no_ssrf("http://multicast.example.com/")

    def test_dns_error_raises_ssrf_dns_error(self):
        """DNS resolution failure must raise SSRFDNSError (fail-closed)."""
        with patch("socket.getaddrinfo", side_effect=OSError("Name or service not known")):
            with pytest.raises(SSRFDNSError):
                validate_no_ssrf("http://nonexistent.invalid/")

    def test_ipv6_loopback_blocked(self):
        """IPv6 loopback ::1 must be blocked."""
        result = (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 0, 0, 0))
        with patch("socket.getaddrinfo", return_value=[result]):
            with pytest.raises(ValueError, match="blocked address"):
                validate_no_ssrf("http://[::1]/")

    def test_ipv6_private_blocked(self):
        """IPv6 private range fc00::/7 must be blocked."""
        result = (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("fc00::1", 0, 0, 0))
        with patch("socket.getaddrinfo", return_value=[result]):
            with pytest.raises(ValueError, match="blocked address"):
                validate_no_ssrf("http://[fc00::1]/")


# ---------------------------------------------------------------------------
# Router-layer behaviour — validate_no_ssrf called by create_url via executor
# ---------------------------------------------------------------------------

class TestRouterSSRFBehaviour:
    def test_dns_error_raises_ssrf_dns_error_not_plain_value_error(self):
        """DNS errors must raise SSRFDNSError (not plain ValueError) so the router
        can return 503 instead of leaking OS errno in a 422 detail string."""
        with patch("socket.getaddrinfo", side_effect=OSError("[Errno -2] Name or service not known")):
            with pytest.raises(SSRFDNSError) as exc_info:
                validate_no_ssrf("http://nonexistent.invalid/")
            assert isinstance(exc_info.value, SSRFDNSError)

    def test_dns_error_is_ssrf_dns_error_subclass(self):
        """SSRFDNSError must be a ValueError subclass so existing ValueError handlers
        catch it as a fallback, but the router catches SSRFDNSError first."""
        assert issubclass(SSRFDNSError, ValueError)

    def test_private_ip_raises_value_error_not_ssrf_dns_error(self):
        """Blocked addresses must raise plain ValueError (not SSRFDNSError)
        so the router returns 422 with structured detail, not 503."""
        with patch("socket.getaddrinfo", return_value=[_addr("192.168.1.1")]):
            with pytest.raises(ValueError) as exc_info:
                validate_no_ssrf("http://internal.example.com/")
            assert type(exc_info.value) is ValueError
            assert "blocked address" in str(exc_info.value)
