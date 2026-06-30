import pytest
from app.utils import anonymize_ip


def test_anonymize_ip_none_returns_none():
    assert anonymize_ip(None) is None


def test_anonymize_ip_invalid_returns_none():
    assert anonymize_ip("not-an-ip") is None


def test_anonymize_ip_ipv4_masks_last_octet():
    assert anonymize_ip("1.2.3.4") == "1.2.3.0"


def test_anonymize_ip_ipv4_already_zero():
    assert anonymize_ip("10.0.0.255") == "10.0.0.0"


def test_anonymize_ip_ipv6_masks_low_80_bits():
    result = anonymize_ip("2001:db8::1")
    addr = result
    # Top 48 bits (first 3 groups) must match; remaining groups zero
    assert addr is not None
    parts = addr.split(":")
    # Expand to 8 groups for reliable comparison
    import ipaddress
    expanded = ipaddress.IPv6Address(addr).exploded.split(":")
    assert expanded[0] == "2001"
    assert expanded[1] == "0db8"
    # Groups 3-8 must be zero (80 bits zeroed)
    assert all(g == "0000" for g in expanded[3:])


def test_anonymize_ip_ipv6_full_address():
    result = anonymize_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
    import ipaddress
    expanded = ipaddress.IPv6Address(result).exploded.split(":")
    assert expanded[0] == "2001"
    assert expanded[1] == "0db8"
    assert all(g == "0000" for g in expanded[3:])
