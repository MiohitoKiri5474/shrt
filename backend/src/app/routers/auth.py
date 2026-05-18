import os
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from jwt import PyJWTError as JWTError
from app.database import get_db
from app.rate_limiter import limiter
from app.models import User
from app.schemas import UserCreate, UserOut, Token
from app.services.auth import hash_password, verify_password, create_access_token, decode_token
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

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
    return await _create_user(data, db)

@limiter.limit("5/minute")
@router.post("/login", response_model=Token)
async def login(request: Request, response: Response, form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="strict",
        secure=_COOKIE_SECURE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"access_token": token, "token_type": "bearer"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}

@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await _create_user(data, db)
