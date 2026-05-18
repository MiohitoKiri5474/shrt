from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_real_ip(request: Request) -> str:
    """Return the real client IP, respecting X-Forwarded-For behind a proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=get_real_ip)
