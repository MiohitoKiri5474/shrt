"""Unit tests for validate_no_ssrf — mocks socket.getaddrinfo to avoid live DNS."""
import socket
from unittest.mock import patch

import pytest

from app.schemas import SSRFDNSError, URLCreate, validate_no_ssrf


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
# URLCreate.block_private_hosts — ensure DNS errors return generic message
# ---------------------------------------------------------------------------

class TestURLCreateBlockPrivateHosts:
    def test_dns_error_generic_message(self):
        """SSRFDNSError must surface as a generic 422 message, not OS error details."""
        with patch("socket.getaddrinfo", side_effect=OSError("[Errno -2] Name or service not known")):
            with pytest.raises(Exception) as exc_info:
                URLCreate(original_url="http://nonexistent.invalid/")
            # Pydantic wraps as ValidationError; detail must NOT expose OS errno
            assert "[Errno" not in str(exc_info.value)
            assert "temporarily unreachable" in str(exc_info.value)

    def test_private_ip_validation_error(self):
        with patch("socket.getaddrinfo", return_value=[_addr("192.168.1.1")]):
            with pytest.raises(Exception) as exc_info:
                URLCreate(original_url="http://internal.example.com/")
            assert "blocked address" in str(exc_info.value)
