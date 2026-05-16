import ipaddress


def anonymize_ip(ip: str | None) -> str | None:
    """Anonymize an IP address for GDPR/CCPA compliance.

    - IPv4: mask the last octet  (e.g. 1.2.3.4  → 1.2.3.0)
    - IPv6: mask the last 80 bits (e.g. 2001:db8::1 → 2001:db8::)

    Returns None when the input is None or cannot be parsed.
    """
    if ip is None:
        return None
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None

    if isinstance(addr, ipaddress.IPv4Address):
        # Zero out the last octet
        network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
        return str(network.network_address)

    # IPv6: keep the top 48 bits, zero the remaining 80 bits
    # RFC 6235 / common practice: retain first /48 prefix
    packed = addr.packed  # 16 bytes
    # Mask: keep first 6 bytes (48 bits), zero remaining 10 bytes (80 bits)
    masked = packed[:6] + b"\x00" * 10
    return str(ipaddress.IPv6Address(masked))
