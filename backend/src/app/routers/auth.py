import os
from datetime import datetime, timezone
import bcrypt as _bcrypt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from jwt import PyJWTError as JWTError
from app.database import get_db
from app.rate_limiter import limiter
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate, Token
from app.services.auth import hash_password, verify_password, create_access_token, decode_token
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Pre-computed bcrypt hash used for constant-time dummy verification.
# Prevents timing side-channels when rejecting unknown users or over-length passwords.
_DUMMY_HASH = "$2b$12$RpzQzS49HHi/fOepHrovVOmBk1bVx5BDBK/zqSvOyJpglJpw8tjA2"

_APP_ENV = os.getenv("APP_ENV", "production").lower()
_COOKIE_SECURE = _APP_ENV not in {"development", "dev"}

async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    cookie_token: str | None = Cookie(default=None, alias="access_token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Cookie takes priority over bearer token — bearer is kept for API clients
    actual_token = cookie_token or token
    if not actual_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(actual_token)
        user_id: int = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def _create_user(data: UserCreate, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    await db.refresh(user)
    return user

@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, data: UserCreate, db: AsyncSession = Depends(get_db)):
    if len(data.password) > 128:
        raise HTTPException(status_code=422, detail="Password too long")
    if os.getenv("ALLOW_REGISTRATION", "false").lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=403, detail="Registration is disabled.")
    try:
        return await _create_user(data, db)
    except HTTPException as exc:
        if exc.status_code == 409:
            # Equalize latency so duplicate vs new registration is indistinguishable
            # by timing (bcrypt would run on a real registration).
            hash_password(data.password)
            raise HTTPException(status_code=409, detail="Email already registered")
        raise

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, response: Response, form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    if len(form.password) > 128:
        # Run a dummy bcrypt check to normalize response time — a bare 401 returns
        # in microseconds while a normal failed login takes ~100ms for bcrypt,
        # letting an attacker distinguish "too long" from "wrong password" by timing.
        verify_password("dummy", _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    identifier = form.username
    if "@" in identifier:
        result = await db.execute(select(User).where(User.email == identifier))
    else:
        result = await db.execute(select(User).where(User.username == identifier))
    user = result.scalar_one_or_none()
    if not user:
        # Three dummy bcrypt ops to match the worst-case wrong-password path:
        # verify_password (op 1) + _bcrypt.checkpw (op 2) + dummy (op 3).
        verify_password("dummy", _DUMMY_HASH)
        verify_password("dummy", _DUMMY_HASH)
        verify_password("dummy", _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(form.password, user.password_hash):
        # Legacy fallback: hashes created before the SHA-256 prehash scheme
        # were produced with plain bcrypt(password). Try raw bcrypt verification;
        # on success transparently re-hash to the current scheme.
        try:
            legacy_ok = _bcrypt.checkpw(form.password.encode(), user.password_hash.encode())
        except Exception:
            legacy_ok = False
        if not legacy_ok:
            # One extra dummy to reach 3 total ops:
            # verify_password (op 1) + _bcrypt.checkpw (op 2) + this dummy (op 3).
            verify_password("dummy", _DUMMY_HASH)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # Upgrade the stored hash to the new SHA-256 prehash scheme.
        user.password_hash = hash_password(form.password)
        await db.commit()
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="strict",
        secure=_COOKIE_SECURE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"token_type": "bearer"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        "access_token",
        httponly=True,
        samesite="strict",
        secure=_COOKIE_SECURE,
        path="/",
    )
    return {"message": "Logged out"}

@router.get("/me", response_model=UserOut)
@limiter.limit("60/minute")
async def me(request: Request, current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserOut)
@limiter.limit("10/minute")
async def update_me(
    request: Request,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check uniqueness (exclude self)
    result = await db.execute(
        select(User).where(User.username == data.username, User.id != current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")
    current_user.username = data.username
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    await db.refresh(current_user)
    return current_user

@router.post("/users", response_model=UserOut, status_code=201)
@limiter.limit("10/minute")
async def create_user(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await _create_user(data, db)
