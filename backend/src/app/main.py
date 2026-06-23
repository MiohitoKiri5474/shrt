import logging
import os
from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.rate_limiter import limiter, _trusted_proxy_nets, _trusted_proxies
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import create_tables, AsyncSessionLocal
from app.models import User
from app.services.auth import hash_password
from app.schemas import UserCreate
from pydantic import ValidationError
from app.routers import auth, urls, redirect

logger = logging.getLogger(__name__)

_WEAK_PASSWORDS = frozenset({
    "changeme1234", "password", "admin", "changeme",
    "123456", "test", "qwerty", "letmein",
})

_APP_ENV = os.getenv("APP_ENV", "production").lower()
_is_dev = _APP_ENV in {"development", "dev"}
_is_non_prod = _APP_ENV in {"development", "dev", "test", "testing"}

app = FastAPI(
    title="URL Shortener API",
    version="1.0.0",
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

@app.on_event("startup")
async def startup():  # pragma: no cover
    if _APP_ENV not in {"development", "dev", "test", "testing"}:
        logger.warning(
            "HSTS is not set at the application layer. "
            "Ensure the TLS-terminating proxy sets: "
            "Strict-Transport-Security: max-age=31536000; includeSubDomains"
        )
    await create_tables()
    await seed_default_user()

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
            try:
                db.add(User(email=email, password_hash=hash_password(password), username=username, is_admin=True))
                await db.commit()
            except IntegrityError:
                await db.rollback()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(urls.router, prefix="/api/urls", tags=["urls"])
app.include_router(redirect.router, tags=["redirect"])
