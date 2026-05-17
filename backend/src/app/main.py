import os
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.rate_limiter import limiter
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import create_tables, AsyncSessionLocal
from app.models import User
from app.services.auth import hash_password
from app.routers import auth, urls, redirect

app = FastAPI(title="URL Shortener API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_APP_ENV = os.getenv("APP_ENV", "production").lower()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        if _APP_ENV not in {"development", "dev"}:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


app.add_middleware(SecurityHeadersMiddleware)

_cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
if _APP_ENV not in {"development", "dev"} and not _cors_origins_env:
    raise ValueError("CORS_ALLOWED_ORIGINS must be set in production")
origins = [o.strip() for o in (_cors_origins_env or "http://localhost:5173,http://localhost:80").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.on_event("startup")
async def startup():  # pragma: no cover
    await create_tables()
    await seed_default_user()

async def seed_default_user():
    email = os.getenv("DEFAULT_USER_EMAIL")
    password = os.getenv("DEFAULT_USER_PASSWORD")
    if not email or not password:
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none() is None:
            try:
                db.add(User(email=email, password_hash=hash_password(password)))
                await db.commit()
            except IntegrityError:
                await db.rollback()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(urls.router, prefix="/api/urls", tags=["urls"])
app.include_router(redirect.router, tags=["redirect"])
