import hashlib
import secrets
import string
import bcrypt
from datetime import datetime, timedelta, timezone
import jwt
from jwt import PyJWTError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import URL
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


def _prehash(password: str) -> bytes:
    # SHA-256 prehash prevents bcrypt's silent 72-byte truncation so all
    # password bytes contribute to the hash regardless of length.
    return hashlib.sha256(password.encode()).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=12)).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_prehash(plain), hashed.encode())

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    to_encode["iat"] = now
    to_encode["iss"] = "shrt"
    to_encode["aud"] = "shrt-api"
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],
                      audience="shrt-api", issuer="shrt")

def generate_short_code(length: int = 8) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))

async def get_unique_short_code(db: AsyncSession, length: int = 8) -> str:
    for _ in range(10):
        code = generate_short_code(length)
        result = await db.execute(select(URL).where(URL.short_code == code))
        if result.scalar_one_or_none() is None:
            return code
    raise RuntimeError("Failed to generate unique short code after 10 attempts")
