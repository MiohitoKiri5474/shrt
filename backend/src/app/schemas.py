from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, field_validator
from datetime import datetime
import ipaddress
import socket
from urllib.parse import urlparse


class SSRFDNSError(ValueError):
    """DNS resolution failed during SSRF check — transient, not a client error."""


def validate_no_ssrf(url: str) -> None:
    """Resolve hostname and block private/internal/reserved/multicast targets.

    Call at both URL-creation time and redirect-serve time to prevent DNS rebinding.
    Uses getaddrinfo to check all resolved IPs, preventing multi-A-record SSRF bypass.

    Raises SSRFDNSError for transient DNS failures, ValueError for blocked addresses.
    """
    try:
        host = urlparse(url).hostname
    except Exception:
        return
    if not host:
        return
    try:
        results = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError as e:
        raise SSRFDNSError(f"Could not resolve hostname for SSRF check: {e}")
    for (_, _, _, _, sockaddr) in results:
        addr = ipaddress.ip_address(sockaddr[0])
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        ):
            raise ValueError(f"URL resolves to a blocked address: {addr}")


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        return v

class UserOut(BaseModel):
    email: str
    created_at: datetime
    model_config = {"from_attributes": True}

class Token(BaseModel):
    token_type: str = "bearer"

class URLCreate(BaseModel):
    original_url: AnyHttpUrl
    custom_code: str | None = Field(None, min_length=3, max_length=16, pattern=r"^[a-zA-Z0-9_-]+$")


class URLOut(BaseModel):
    id: int
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int = 0
    model_config = {"from_attributes": True}

class StatsOut(BaseModel):
    url_id: int
    short_code: str
    original_url: str
    total_clicks: int
    clicks_by_date: dict[str, int]
