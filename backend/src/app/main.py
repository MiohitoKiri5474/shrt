import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import create_tables, AsyncSessionLocal
from app.models import User
from app.services.auth import hash_password
from app.schemas import UserCreate
from pydantic import ValidationError
from app.routers import auth, urls, redirect

logger = logging.getLogger(__name__)

app = FastAPI(title="URL Shortener API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    try:
        UserCreate(email=email, password=password)
    except ValidationError:
        logger.warning("seed_default_user: skipping — DEFAULT_USER_PASSWORD failed schema validation")
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
