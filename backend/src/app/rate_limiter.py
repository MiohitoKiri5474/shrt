import ipaddress
import os
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

_trusted_proxies_env = os.getenv("TRUSTED_PROXY_IPS", "")
_trusted_proxies = {s.strip() for s in _trusted_proxies_env.split(",") if s.strip()}


def _is_trusted_proxy(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or ip in _trusted_proxies
    except ValueError:
        return False


def get_real_ip(request: Request) -> str:
    """Return real client IP.

    Only trusts X-Forwarded-For when the direct connection is from a private
    network or an IP listed in TRUSTED_PROXY_IPS. Prevents IP spoofing via
    forged XFF headers bypassing per-IP rate limits (H-7).
    """
    direct_ip = get_remote_address(request)
    if _is_trusted_proxy(direct_ip):
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    return direct_ip


limiter = Limiter(key_func=get_real_ip)
