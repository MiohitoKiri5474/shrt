import ipaddress
import logging
import os
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

# TRUSTED_PROXY_CIDRS: comma-separated CIDR ranges for known reverse proxies.
# Set to the Docker bridge/overlay network used by nginx (e.g. "172.16.0.0/12").
# Trusting all private IPs is too broad; any container on the host would be
# treated as a trusted proxy and could inject a forged X-Forwarded-For prefix.
_trusted_proxy_nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
for _cidr in os.getenv("TRUSTED_PROXY_CIDRS", "").split(","):
    _cidr = _cidr.strip()
    if _cidr:
        try:
            _trusted_proxy_nets.append(ipaddress.ip_network(_cidr, strict=False))
        except ValueError:
            logging.warning("TRUSTED_PROXY_CIDRS: invalid CIDR %r ignored", _cidr)

# TRUSTED_PROXY_IPS: comma-separated individual IPs for proxies that don't fit
# neatly into a CIDR (e.g. a fixed load-balancer VIP).
_trusted_proxies = {
    s.strip()
    for s in os.getenv("TRUSTED_PROXY_IPS", "").split(",")
    if s.strip()
}


def _is_trusted_proxy(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in _trusted_proxy_nets) or ip in _trusted_proxies
    except ValueError:
        return False


def get_real_ip(request: Request) -> str:
    """Return real client IP.

    Only trusts X-Forwarded-For when the direct connection originates from an
    IP within TRUSTED_PROXY_CIDRS or TRUSTED_PROXY_IPS. Prevents IP spoofing
    via forged XFF headers that bypass per-IP rate limits.
    """
    direct_ip = get_remote_address(request)
    if _is_trusted_proxy(direct_ip):
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(",")]
            for ip in reversed(ips):
                if not _is_trusted_proxy(ip):
                    return ip
            return ips[0]
    return direct_ip


if not _trusted_proxy_nets and not _trusted_proxies:
    logging.warning(
        "TRUSTED_PROXY_CIDRS is empty — per-IP rate limiting disabled; "
        "all requests will share one rate-limit bucket. "
        "Set TRUSTED_PROXY_CIDRS to your Docker bridge subnet: "
        "docker network inspect <project>_app-net --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'"
    )

_redis_url = os.getenv("REDIS_URL")
if not _redis_url:
    import logging
    logging.getLogger(__name__).warning(
        "REDIS_URL not set — using in-memory rate limiter (not suitable for production)"
    )
    _redis_url = "memory://"
limiter = Limiter(key_func=get_real_ip, storage_uri=_redis_url)
