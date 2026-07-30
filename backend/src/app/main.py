import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.rate_limiter import limiter, _trusted_proxy_nets, _trusted_proxies
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import run_migrations, AsyncSessionLocal
from app.models import User
from app.services.auth import hash_password_async
from app.schemas import UserCreate
from pydantic import ValidationError
from app.routers import auth, urls, redirect, admin

logger = logging.getLogger(__name__)

_WEAK_PASSWORDS = frozenset({
    "changeme1234", "password", "admin", "changeme",
    "123456", "test", "qwerty", "letmein",
})

_APP_ENV = os.getenv("APP_ENV", "production").lower()
_is_dev = _APP_ENV in {"development", "dev"}
_is_non_prod = _APP_ENV in {"development", "dev", "test", "testing"}

@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    if _APP_ENV not in {"development", "dev", "test", "testing"}:
        logger.warning(
            "HSTS is not set at the application layer. "
            "Ensure the TLS-terminating proxy sets: "
            "Strict-Transport-Security: max-age=31536000; includeSubDomains"
        )
    await run_migrations()
    await seed_default_user()
    yield

app = FastAPI(
    title="Shrt API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data: https:; connect-src 'self'; font-src 'self'; "
            "frame-ancestors 'none'; frame-src 'none'; object-src 'none'; "
            "base-uri 'self'; form-action 'self';"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        # HSTS must be set by the TLS-terminating reverse proxy or CDN, not here.
        # This server only handles HTTP; browsers ignore HSTS on non-HTTPS responses.
        return response


app.add_middleware(SecurityHeadersMiddleware)

_cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
if not _is_dev and not _cors_origins_env:
    raise ValueError("CORS_ALLOWED_ORIGINS must be set in production")
origins = [o.strip() for o in (_cors_origins_env or "http://localhost:5173,http://localhost:80").split(",") if o.strip()]

# Fail fast in production when no trusted proxies are configured. Without this,
# the real client IP behind nginx can't be determined, so every request shares
# one rate-limit bucket and a single user can exhaust limits for everyone.
if not _is_non_prod and not _trusted_proxy_nets and not _trusted_proxies:
    raise ValueError(
        "TRUSTED_PROXY_CIDRS must be set in production to enable per-IP rate limiting. "
        "Find your Docker bridge CIDR with: "
        "docker network inspect <project>_app-net "
        "--format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

def compute_allowed_hosts(allowed_hosts_env: str | None, is_dev: bool, cors_origins: list[str]) -> list[str]:
    """Resolve the TrustedHostMiddleware allowlist.

    Prefers an explicit ALLOWED_HOSTS env var; otherwise derives hostnames from
    the CORS origins (the backend is normally reached under the same host as
    the frontend, behind one reverse proxy). In dev, falls back to "*" so local
    tooling (and the test client's synthetic Host header) is never blocked.
    Raises if no hosts can be resolved outside dev — silently defaulting to "*"
    in production would defeat the point of the check.
    """
    if allowed_hosts_env:
        return [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]
    if is_dev:
        return ["*"]
    hosts = sorted({h for o in cors_origins if (h := urlparse(o).hostname)})
    if not hosts:
        raise ValueError(
            "Could not derive allowed hosts from CORS_ALLOWED_ORIGINS. Set ALLOWED_HOSTS "
            "explicitly (comma-separated hostnames, e.g. yourdomain.com)."
        )
    return hosts


# Reject requests with a forged/unexpected Host header. Without this, an
# attacker-controlled Host is reflected into the QR-code short link built from
# request.base_url (routers/urls.py get_qr_code). Defaults to the hostnames
# already trusted for CORS; set ALLOWED_HOSTS to override when the backend is
# reachable under a different host than the frontend origins.
allowed_hosts = compute_allowed_hosts(os.getenv("ALLOWED_HOSTS"), _is_dev, origins)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

@app.get("/health")
@limiter.limit("30/minute")
async def health(request: Request):
    return {"status": "ok"}


# Same payload as /health, but mounted under /api so the frontend can reach it
# through nginx's `/api/*` reverse-proxy rule. Used by the UI to poll backend
# connectivity. The limit is generous (a 30s client poll is ~2 req/min) so the
# liveness probe never trips its own rate limit and false-reports "offline".
@app.get("/api/health")
@limiter.limit("60/minute")
async def api_health(request: Request) -> dict[str, str]:
    return {"status": "ok"}

async def seed_default_user():
    email = os.getenv("DEFAULT_USER_EMAIL")
    password = os.getenv("DEFAULT_USER_PASSWORD")
    username = os.getenv("DEFAULT_USER_USERNAME") or None
    if not email or not password:
        return
    if password.lower() in _WEAK_PASSWORDS:
        msg = (
            "DEFAULT_USER_PASSWORD is set to a known weak password. "
            "Update it to a strong unique value before deploying."
        )
        if _APP_ENV in {"production", "prod"}:
            raise RuntimeError(msg)
        logger.critical(msg)
    try:
        UserCreate(email=email, password=password)
    except ValidationError:
        raise ValueError(
            "DEFAULT_USER_PASSWORD failed schema validation — "
            "refusing to start with invalid seed credentials"
        )
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none() is None:
            password_hash = await hash_password_async(password)
            try:
                db.add(User(email=email, password_hash=password_hash, username=username, is_admin=True))
                await db.commit()
            except IntegrityError:
                await db.rollback()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(urls.router, prefix="/api/urls", tags=["urls"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(redirect.router, tags=["redirect"])
