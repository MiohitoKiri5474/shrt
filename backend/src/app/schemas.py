from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, field_validator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import ipaddress
import socket
from urllib.parse import urlparse

# Dedicated executor for SSRF DNS checks — isolates slow getaddrinfo calls from the
# shared default executor so DNS-amplification attacks cannot starve other async tasks.
_SSRF_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ssrf-check")

# Seconds to wait for a single SSRF DNS check before aborting.
_SSRF_CHECK_TIMEOUT_S = 5.0


class SSRFDNSError(ValueError):
    """DNS resolution failed during SSRF check — transient, not a client error."""


class SSRFBlockedError(ValueError):
    """URL resolved to a blocked address. Carries blocked_addr for server-side logging
    without leaking the IP in the public error message."""

    def __init__(self, addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
        super().__init__("URL resolves to a blocked or internal address")
        self.blocked_addr = addr


def validate_no_ssrf(url: str) -> None:
    """Resolve hostname and allow only globally-routable targets.

    Call at both URL-creation time and redirect-serve time to prevent DNS rebinding.
    Uses getaddrinfo to check all resolved IPs, preventing multi-A-record SSRF bypass.

    Takes an allowlist stance (``not addr.is_global``) rather than enumerating
    individual non-routable ranges: private/loopback/link-local are checked
    explicitly for clarity, but ``is_global`` also closes ranges those checks
    miss — e.g. RFC 6598 carrier-grade NAT (100.64.0.0/10), 0.0.0.0/8, and any
    future reserved space — without needing a new condition for each one.

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
            or not addr.is_global
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

class EmailChange(BaseModel):
    current_password: str
    new_email: EmailStr

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        return v

class AdminUserOut(BaseModel):
    id: int
    email: str
    username: str | None = None
    is_admin: bool
    created_at: datetime
    url_count: int = 0
    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    is_admin: bool


class Token(BaseModel):
    token_type: str = "bearer"

class URLCreate(BaseModel):
    original_url: AnyHttpUrl
    custom_code: str | None = Field(None, min_length=6, max_length=16, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str | None = Field(None, min_length=6, max_length=128)

    @field_validator("original_url", mode="before")
    @classmethod
    def url_max_length(cls, v: object) -> object:
        if isinstance(v, str) and len(v) > 2048:
            raise ValueError("URL must not exceed 2048 characters")
        return v


class URLUpdate(BaseModel):
    short_code: str = Field(..., min_length=3, max_length=16, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = ""
    remove_password: bool = False
    expires_at: datetime | None = None

    @field_validator("expires_at", mode="after")
    @classmethod
    def expires_must_be_future(cls, v: object) -> object:
        if v is None:
            return v
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError("Expiry must be in the future")
        return v



class URLOut(BaseModel):
    id: int
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int = 0
    has_password: bool = False
    expires_at: datetime | None = None
    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_clicks(cls, url: object, click_count: int) -> "URLOut":
        return cls.model_validate(url).model_copy(update={
            "click_count": click_count,
            "has_password": bool(getattr(url, "password_hash", None)),
        })


class PasswordVerify(BaseModel):
    password: str = Field(..., min_length=6, max_length=128)


class UnlockOut(BaseModel):
    redirect_url: str

class StatsOut(BaseModel):
    url_id: int
    short_code: str
    original_url: str
    total_clicks: int
    clicks_by_date: dict[str, int]
