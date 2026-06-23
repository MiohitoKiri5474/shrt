from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, field_validator
from datetime import datetime
import ipaddress
import socket
from urllib.parse import urlparse


class SSRFDNSError(ValueError):
    """DNS resolution failed during SSRF check — transient, not a client error."""


class SSRFBlockedError(ValueError):
    """URL resolved to a blocked address. Carries blocked_addr for server-side logging
    without leaking the IP in the public error message."""

    def __init__(self, addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
        super().__init__("URL resolves to a blocked or internal address")
        self.blocked_addr = addr


def validate_no_ssrf(url: str) -> None:
    """Resolve hostname and block private/internal/reserved/multicast targets.

    Call at both URL-creation time and redirect-serve time to prevent DNS rebinding.
    Uses getaddrinfo to check all resolved IPs, preventing multi-A-record SSRF bypass.

    Raises SSRFDNSError for transient DNS failures, SSRFBlockedError for blocked addresses.
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
        raise SSRFDNSError("URL destination temporarily unreachable")
    for (_, _, _, _, sockaddr) in results:
        addr = ipaddress.ip_address(sockaddr[0])
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        ):
            raise SSRFBlockedError(addr)


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
    is_admin: bool
    username: str | None = None
    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")

class AdminUserOut(BaseModel):
    id: int
    email: str
    username: str | None = None
    is_admin: bool
    created_at: datetime
    url_count: int = 0
    model_config = {"from_attributes": True}

class Token(BaseModel):
    token_type: str = "bearer"

class URLCreate(BaseModel):
    original_url: AnyHttpUrl
    custom_code: str | None = Field(None, min_length=3, max_length=16, pattern=r"^[a-zA-Z0-9_-]+$")

    @field_validator("original_url", mode="before")
    @classmethod
    def url_max_length(cls, v: object) -> object:
        if isinstance(v, str) and len(v) > 2048:
            raise ValueError("URL must not exceed 2048 characters")
        return v



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
