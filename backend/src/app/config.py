import os

SECRET_KEY = os.environ["SECRET_KEY"]  # KeyError if missing — intentional
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./shortener.db")
