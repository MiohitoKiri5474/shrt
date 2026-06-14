# URL Shortener Fullstack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fullstack URL shortener with Vue3+Bun frontend and FastAPI+uv backend, both containerized, supporting user auth, URL CRUD, and click statistics.

**Architecture:** Three-layer system — FastAPI backend exposes a REST API with JWT auth, Vue3 SPA consumes the API, both run in separate Docker containers orchestrated by docker-compose. Short codes are random 8-char alphanumeric strings stored in SQLite via async SQLAlchemy. Click events are recorded on each redirect and aggregated for stats.

**Tech Stack:** Python 3.12, FastAPI, uv, SQLAlchemy 2.0 async, aiosqlite, python-jose, passlib, pytest, httpx | Vue3, Bun, Pinia, Vue Router, Axios, Vitest, @vue/test-utils | Docker, docker-compose

---

## Subsystem Decomposition

Three subsystems developed in parallel via git worktrees:
- **A: Backend** → `feature/backend` worktree
- **B: Frontend** → `feature/frontend` worktree
- **C: Docker/Integration** → composed on develop after A+B merge

---

## File Map

```
url-shortener-fullstack/
├── .gitignore
├── README.md
├── docker-compose.yml
├── docker-compose.override.yml
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── src/
│   │   ├── __init__.py
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py            # FastAPI app, CORS, router registration
│   │       ├── config.py          # Env-based config (SECRET_KEY, DB_URL)
│   │       ├── database.py        # Async engine, session factory, create_tables
│   │       ├── models.py          # User, URL, Click ORM models
│   │       ├── schemas.py         # Pydantic request/response schemas
│   │       ├── routers/
│   │       │   ├── __init__.py
│   │       │   ├── auth.py        # /api/auth/* endpoints
│   │       │   ├── urls.py        # /api/urls/* endpoints + stats
│   │       │   └── redirect.py    # /{short_code} redirect + click tracking
│   │       └── services/
│   │           ├── __init__.py
│   │           └── auth.py        # JWT, password hashing, short code gen
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_auth.py
│       ├── test_urls.py
│       └── test_stats.py
└── frontend/
    ├── package.json
    ├── Dockerfile
    ├── nginx.conf
    ├── .dockerignore
    ├── .env.production
    └── src/
        ├── api/
        │   ├── client.ts          # Axios instance, token interceptor, 401 redirect
        │   ├── auth.ts            # register, login, me
        │   └── urls.ts            # list, create, remove, stats
        ├── stores/
        │   ├── auth.ts            # Pinia: user, isAuthenticated, login, logout, restore
        │   ├── urls.ts            # Pinia: urls, currentStats, fetchAll, create, remove, fetchStats
        │   └── __tests__/
        │       ├── auth.spec.ts
        │       └── urls.spec.ts
        ├── views/
        │   ├── LoginView.vue      # Email/password form → auth store
        │   └── DashboardView.vue  # URL list + stats panel + header
        ├── components/
        │   ├── CreateURLForm.vue  # Create URL form (original + optional custom code)
        │   └── URLCard.vue        # URL row: copy, stats, delete actions
        └── router/
            └── index.ts           # Routes, auth guard via store.restore()
```

## API Contract

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | No | Register user |
| POST | `/api/auth/login` | No | Login → JWT |
| GET | `/api/auth/me` | Yes | Current user |
| GET | `/api/urls` | Yes | List user's URLs |
| POST | `/api/urls` | Yes | Create short URL |
| DELETE | `/api/urls/{id}` | Yes | Delete URL |
| GET | `/api/urls/{id}/stats` | Yes | URL stats |
| GET | `/{short_code}` | No | Redirect → original |

---

## Phase 0: Git & Worktree Setup

### Task 0.1: Initialize Repository

**Files:**
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Init git repo and create base branches**

```bash
cd /Users/miohitokiri5474/project/url-shortener-fullstack
git init
git checkout -b main
```

- [ ] **Step 2: Create .gitignore**

```
# Python
__pycache__/
*.pyc
*.pyo
.venv/
.uv/
*.egg-info/
dist/
.pytest_cache/
htmlcov/
.coverage

# Node / Bun
node_modules/
.bun/
dist/
coverage/

# DB
*.db
*.sqlite

# Env
.env
.env.local
.env.*.local

# Docker
.dockerignore

# IDE
.vscode/
.idea/
*.swp
```

- [ ] **Step 3: Create README**

```markdown
# URL Shortener

Fullstack URL shortener — Vue3 frontend, FastAPI backend, Docker.

## Quick Start

```bash
docker-compose up --build
```

Frontend: http://localhost:80
Backend API: http://localhost:8000/docs
```

- [ ] **Step 4: Initial commit on main**

```bash
git add .gitignore README.md
git commit -m "chore: initial project scaffold"
```

- [ ] **Step 5: Create develop branch**

```bash
git checkout -b develop
```

---

### Task 0.2: Create Git Worktrees

- [ ] **Step 1: Create backend worktree**

```bash
git worktree add ../url-shortener-backend feature/backend
```

Expected: `Preparing worktree (new branch 'feature/backend')`

- [ ] **Step 2: Create frontend worktree**

```bash
git worktree add ../url-shortener-frontend feature/frontend
```

Expected: `Preparing worktree (new branch 'feature/frontend')`

- [ ] **Step 3: Verify worktrees**

```bash
git worktree list
```

Expected:
```
/Users/miohitokiri5474/project/url-shortener-fullstack      <hash> [develop]
/Users/miohitokiri5474/project/url-shortener-backend        <hash> [feature/backend]
/Users/miohitokiri5474/project/url-shortener-frontend       <hash> [feature/frontend]
```

---

## Phase 1: Backend (in `../url-shortener-backend`)

All steps run inside `../url-shortener-backend/`.

### Task 1.1: Project Structure + uv Setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/app/__init__.py`
- Create: `backend/src/app/main.py`
- Create: `backend/src/app/config.py`

- [ ] **Step 1: Create backend directory and init uv project**

```bash
cd ../url-shortener-backend
mkdir backend && cd backend
uv init --no-workspace
```

- [ ] **Step 2: Add dependencies**

```bash
uv add fastapi uvicorn[standard] sqlalchemy aiosqlite python-jose[cryptography] passlib[bcrypt] python-multipart
uv add --dev pytest pytest-asyncio httpx coverage
```

- [ ] **Step 3: Append tool config to pyproject.toml**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.coverage.run]
source = ["src"]
omit = ["tests/*"]
```

- [ ] **Step 4: Create src layout**

```bash
mkdir -p src/app tests
touch src/__init__.py src/app/__init__.py tests/__init__.py
```

- [ ] **Step 5: Write config.py**

```python
# backend/src/app/config.py
import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./shortener.db")
```

- [ ] **Step 6: Write main.py**

```python
# backend/src/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_tables
from app.routers import auth, urls, redirect

app = FastAPI(title="URL Shortener API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await create_tables()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(urls.router, prefix="/api/urls", tags=["urls"])
app.include_router(redirect.router, tags=["redirect"])
```

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "chore: backend project structure and uv setup"
```

---

### Task 1.2: Database Models

**Files:**
- Create: `backend/src/app/database.py`
- Create: `backend/src/app/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, URL, Click

@pytest.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s

async def test_user_model(session):
    user = User(email="test@example.com", password_hash="hashed")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    assert user.id is not None
    assert user.email == "test@example.com"

async def test_url_model(session):
    user = User(email="u@example.com", password_hash="h")
    session.add(user)
    await session.commit()
    url = URL(user_id=user.id, original_url="https://example.com", short_code="abc12345")
    session.add(url)
    await session.commit()
    await session.refresh(url)
    assert url.id is not None
    assert url.short_code == "abc12345"

async def test_click_model(session):
    user = User(email="c@example.com", password_hash="h")
    session.add(user)
    await session.commit()
    url = URL(user_id=user.id, original_url="https://example.com", short_code="xxxxxxxx")
    session.add(url)
    await session.commit()
    click = Click(url_id=url.id, ip_address="127.0.0.1", user_agent="test-agent")
    session.add(click)
    await session.commit()
    await session.refresh(click)
    assert click.id is not None
```

- [ ] **Step 2: Run — confirm FAIL**

```bash
cd backend && uv run pytest tests/test_models.py -v
```

Expected: `ImportError` — `app.models` not found

- [ ] **Step 3: Write database.py**

```python
# backend/src/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL
from app.models import Base

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 4: Write models.py**

```python
# backend/src/app/models.py
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    urls: Mapped[list["URL"]] = relationship("URL", back_populates="user", cascade="all, delete")

class URL(Base):
    __tablename__ = "urls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    short_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    user: Mapped["User"] = relationship("User", back_populates="urls")
    clicks: Mapped[list["Click"]] = relationship("Click", back_populates="url", cascade="all, delete")

class Click(Base):
    __tablename__ = "clicks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url_id: Mapped[int] = mapped_column(Integer, ForeignKey("urls.id"), nullable=False)
    clicked_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(512), nullable=True)
    url: Mapped["URL"] = relationship("URL", back_populates="clicks")
```

- [ ] **Step 5: Run — confirm PASS**

```bash
uv run pytest tests/test_models.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: database models for User, URL, Click"
```

---

### Task 1.3: Auth Service + Router

**Files:**
- Create: `backend/src/app/services/auth.py`
- Create: `backend/src/app/schemas.py`
- Create: `backend/src/app/routers/__init__.py`
- Create: `backend/src/app/routers/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_auth.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base

@pytest.fixture(autouse=True)
async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    AsyncTestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async def override_get_db():
        async with AsyncTestSession() as s:
            yield s
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

async def test_register(client):
    resp = await client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    assert resp.status_code == 201
    assert resp.json()["email"] == "a@b.com"

async def test_register_duplicate(client):
    await client.post("/api/auth/register", json={"email": "dup@b.com", "password": "secret123"})
    resp = await client.post("/api/auth/register", json={"email": "dup@b.com", "password": "other"})
    assert resp.status_code == 409

async def test_login_success(client):
    await client.post("/api/auth/register", json={"email": "login@b.com", "password": "pass1234"})
    resp = await client.post("/api/auth/login", data={"username": "login@b.com", "password": "pass1234"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={"email": "x@b.com", "password": "correct"})
    resp = await client.post("/api/auth/login", data={"username": "x@b.com", "password": "wrong"})
    assert resp.status_code == 401

async def test_me_endpoint(client):
    await client.post("/api/auth/register", json={"email": "me@b.com", "password": "pass1234"})
    login = await client.post("/api/auth/login", data={"username": "me@b.com", "password": "pass1234"})
    token = login.json()["access_token"]
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@b.com"
```

- [ ] **Step 2: Run — confirm FAIL**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: `ImportError` or `404`

- [ ] **Step 3: Write schemas.py**

```python
# backend/src/app/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime
    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class URLCreate(BaseModel):
    original_url: str
    custom_code: str | None = None

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
```

- [ ] **Step 4: Write services/auth.py**

```python
# backend/src/app/services/auth.py
import secrets
import string
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import URL
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

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
```

- [ ] **Step 5: Write routers/auth.py**

```python
# backend/src/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, Token
from app.services.auth import hash_password, verify_password, create_access_token, decode_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        user_id: int = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 6: Create package dirs**

```bash
mkdir -p src/app/routers src/app/services
touch src/app/routers/__init__.py src/app/services/__init__.py
```

- [ ] **Step 7: Run — confirm PASS**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: `5 passed`

- [ ] **Step 8: Commit**

```bash
git add .
git commit -m "feat: auth endpoints — register, login, JWT, /me"
```

---

### Task 1.4: URL CRUD + Redirect

**Files:**
- Create: `backend/src/app/routers/urls.py`
- Create: `backend/src/app/routers/redirect.py`
- Create: `backend/tests/test_urls.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_urls.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base

@pytest.fixture(autouse=True)
async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    AsyncTestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async def override_get_db():
        async with AsyncTestSession() as s:
            yield s
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={"email": "owner@b.com", "password": "pass1234"})
    resp = await client.post("/api/auth/login", data={"username": "owner@b.com", "password": "pass1234"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

async def test_create_url(client, auth_headers):
    resp = await client.post("/api/urls", json={"original_url": "https://example.com"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["original_url"] == "https://example.com"
    assert len(data["short_code"]) == 8

async def test_list_urls(client, auth_headers):
    await client.post("/api/urls", json={"original_url": "https://a.com"}, headers=auth_headers)
    await client.post("/api/urls", json={"original_url": "https://b.com"}, headers=auth_headers)
    resp = await client.get("/api/urls", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

async def test_delete_url(client, auth_headers):
    create = await client.post("/api/urls", json={"original_url": "https://del.com"}, headers=auth_headers)
    url_id = create.json()["id"]
    resp = await client.delete(f"/api/urls/{url_id}", headers=auth_headers)
    assert resp.status_code == 204

async def test_delete_url_not_owner(client, auth_headers):
    create = await client.post("/api/urls", json={"original_url": "https://priv.com"}, headers=auth_headers)
    url_id = create.json()["id"]
    await client.post("/api/auth/register", json={"email": "other@b.com", "password": "pass1234"})
    other_login = await client.post("/api/auth/login", data={"username": "other@b.com", "password": "pass1234"})
    other_token = other_login.json()["access_token"]
    resp = await client.delete(f"/api/urls/{url_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403

async def test_redirect(client, auth_headers):
    create = await client.post("/api/urls", json={"original_url": "https://redirect.com"}, headers=auth_headers)
    code = create.json()["short_code"]
    resp = await client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://redirect.com"
```

- [ ] **Step 2: Run — confirm FAIL**

```bash
uv run pytest tests/test_urls.py -v
```

Expected: `ImportError` — routers not defined

- [ ] **Step 3: Write routers/urls.py**

```python
# backend/src/app/routers/urls.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import URL, Click, User
from app.schemas import URLCreate, URLOut, StatsOut
from app.services.auth import get_unique_short_code
from app.routers.auth import get_current_user

router = APIRouter()

@router.post("", response_model=URLOut, status_code=201)
async def create_url(
    data: URLCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.custom_code:
        result = await db.execute(select(URL).where(URL.short_code == data.custom_code))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Short code already taken")
        code = data.custom_code
    else:
        code = await get_unique_short_code(db)
    url = URL(user_id=current_user.id, original_url=str(data.original_url), short_code=code)
    db.add(url)
    await db.commit()
    await db.refresh(url)
    click_count = await db.scalar(select(func.count()).where(Click.url_id == url.id))
    item = URLOut.model_validate(url)
    item.click_count = click_count or 0
    return item

@router.get("", response_model=list[URLOut])
async def list_urls(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(URL).where(URL.user_id == current_user.id).order_by(URL.created_at.desc())
    )
    urls = result.scalars().all()
    out = []
    for url in urls:
        count = await db.scalar(select(func.count()).where(Click.url_id == url.id))
        item = URLOut.model_validate(url)
        item.click_count = count or 0
        out.append(item)
    return out

@router.delete("/{url_id}", status_code=204)
async def delete_url(
    url_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(URL).where(URL.id == url_id))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    if url.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your URL")
    await db.delete(url)
    await db.commit()

@router.get("/{url_id}/stats", response_model=StatsOut)
async def get_stats(
    url_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(URL).where(URL.id == url_id))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    if url.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your URL")
    total = await db.scalar(select(func.count()).where(Click.url_id == url_id)) or 0
    date_rows = await db.execute(
        select(func.date(Click.clicked_at), func.count())
        .where(Click.url_id == url_id)
        .group_by(func.date(Click.clicked_at))
    )
    clicks_by_date = {str(row[0]): row[1] for row in date_rows}
    return StatsOut(
        url_id=url.id,
        short_code=url.short_code,
        original_url=url.original_url,
        total_clicks=total,
        clicks_by_date=clicks_by_date,
    )
```

- [ ] **Step 4: Write routers/redirect.py**

```python
# backend/src/app/routers/redirect.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import URL, Click

router = APIRouter()

@router.get("/{short_code}")
async def redirect(short_code: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    click = Click(url_id=url.id, ip_address=client_ip, user_agent=user_agent)
    db.add(click)
    await db.commit()
    return RedirectResponse(url=url.original_url, status_code=302)
```

- [ ] **Step 5: Run — confirm PASS**

```bash
uv run pytest tests/test_urls.py -v
```

Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: URL CRUD, redirect with click tracking, stats endpoint"
```

---

### Task 1.5: Stats Tests + Coverage Check

**Files:**
- Create: `backend/tests/test_stats.py`

- [ ] **Step 1: Write stats tests**

```python
# backend/tests/test_stats.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base

@pytest.fixture(autouse=True)
async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    AsyncTestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async def override_get_db():
        async with AsyncTestSession() as s:
            yield s
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.fixture
async def url_with_clicks(client):
    await client.post("/api/auth/register", json={"email": "s@b.com", "password": "pass1234"})
    login = await client.post("/api/auth/login", data={"username": "s@b.com", "password": "pass1234"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post("/api/urls", json={"original_url": "https://stats.com"}, headers=headers)
    url_data = create.json()
    await client.get(f"/{url_data['short_code']}", follow_redirects=False)
    await client.get(f"/{url_data['short_code']}", follow_redirects=False)
    return url_data["id"], headers

async def test_stats_total_clicks(client, url_with_clicks):
    url_id, headers = url_with_clicks
    resp = await client.get(f"/api/urls/{url_id}/stats", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total_clicks"] == 2

async def test_stats_by_date(client, url_with_clicks):
    url_id, headers = url_with_clicks
    resp = await client.get(f"/api/urls/{url_id}/stats", headers=headers)
    data = resp.json()
    assert len(data["clicks_by_date"]) >= 1

async def test_stats_forbidden_for_non_owner(client, url_with_clicks):
    url_id, _ = url_with_clicks
    await client.post("/api/auth/register", json={"email": "other@b.com", "password": "pass1234"})
    login = await client.post("/api/auth/login", data={"username": "other@b.com", "password": "pass1234"})
    other_token = login.json()["access_token"]
    resp = await client.get(f"/api/urls/{url_id}/stats", headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403
```

- [ ] **Step 2: Run full suite**

```bash
uv run pytest -v --tb=short
```

Expected: all pass

- [ ] **Step 3: Check coverage**

```bash
uv run coverage run -m pytest && uv run coverage report --fail-under=80
```

Expected: `>= 80%`

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "test: stats endpoint tests, coverage >= 80%"
```

---

### Task 1.6: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [ ] **Step 1: Write Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/

ENV PYTHONPATH=/app/src
ENV DATABASE_URL=sqlite+aiosqlite:///./data/shortener.db

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write .dockerignore**

```
__pycache__/
*.pyc
.venv/
tests/
*.db
.coverage
htmlcov/
```

- [ ] **Step 3: Build and smoke-test**

```bash
docker build -t url-shortener-backend ./backend
docker run --rm -d -p 8000:8000 --name be-test url-shortener-backend
sleep 3
curl -sf http://localhost:8000/docs > /dev/null && echo "backend OK" || echo "backend FAIL"
docker stop be-test
```

Expected: `backend OK`

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "chore: backend Dockerfile"
```

---

### Task 1.7: Merge Backend to Develop

- [ ] **Step 1: Final test run in backend worktree**

```bash
cd ../url-shortener-backend/backend && uv run pytest -v
```

Expected: all pass

- [ ] **Step 2: Switch to main repo and merge**

```bash
cd /Users/miohitokiri5474/project/url-shortener-fullstack
git merge feature/backend --no-ff -m "feat: merge backend — auth, URL CRUD, stats, Docker"
```

- [ ] **Step 3: Remove backend worktree**

```bash
git worktree remove ../url-shortener-backend
```

---

## Phase 2: Frontend (in `../url-shortener-frontend`)

All steps run inside `../url-shortener-frontend/`.

### Task 2.1: Vue3 + Bun Project Setup

**Files:**
- Create: `frontend/` (scaffolded via bun create vue)
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/urls.ts`

- [ ] **Step 1: Scaffold Vue3 project**

```bash
cd ../url-shortener-frontend
bunx create-vue@latest frontend --typescript --router --pinia --vitest --eslint
cd frontend
bun install
```

- [ ] **Step 2: Add axios**

```bash
bun add axios
```

- [ ] **Step 3: Create API client**

```typescript
// frontend/src/api/client.ts
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)
```

- [ ] **Step 4: Create auth API module**

```typescript
// frontend/src/api/auth.ts
import { apiClient } from './client'

export interface UserOut {
  id: number
  email: string
  created_at: string
}

export interface Token {
  access_token: string
  token_type: string
}

export const authApi = {
  async register(email: string, password: string): Promise<UserOut> {
    const { data } = await apiClient.post<UserOut>('/api/auth/register', { email, password })
    return data
  },
  async login(email: string, password: string): Promise<Token> {
    const form = new URLSearchParams({ username: email, password })
    const { data } = await apiClient.post<Token>('/api/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data
  },
  async me(): Promise<UserOut> {
    const { data } = await apiClient.get<UserOut>('/api/auth/me')
    return data
  },
}
```

- [ ] **Step 5: Create URLs API module**

```typescript
// frontend/src/api/urls.ts
import { apiClient } from './client'

export interface URLOut {
  id: number
  short_code: string
  original_url: string
  created_at: string
  click_count: number
}

export interface StatsOut {
  url_id: number
  short_code: string
  original_url: string
  total_clicks: number
  clicks_by_date: Record<string, number>
}

export const urlsApi = {
  async create(original_url: string, custom_code?: string): Promise<URLOut> {
    const { data } = await apiClient.post<URLOut>('/api/urls', { original_url, custom_code })
    return data
  },
  async list(): Promise<URLOut[]> {
    const { data } = await apiClient.get<URLOut[]>('/api/urls')
    return data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/api/urls/${id}`)
  },
  async stats(id: number): Promise<StatsOut> {
    const { data } = await apiClient.get<StatsOut>(`/api/urls/${id}/stats`)
    return data
  },
}
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "chore: Vue3 + Bun scaffold with typed API client"
```

---

### Task 2.2: Auth Store + Login View

**Files:**
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/router/index.ts`
- Create: `frontend/src/stores/__tests__/auth.spec.ts`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/stores/__tests__/auth.spec.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'
import * as authApiModule from '../../api/auth'

vi.mock('../../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
    register: vi.fn(),
  },
}))

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('login stores token and sets user', async () => {
    vi.mocked(authApiModule.authApi.login).mockResolvedValue({ access_token: 'tok123', token_type: 'bearer' })
    vi.mocked(authApiModule.authApi.me).mockResolvedValue({ id: 1, email: 'a@b.com', created_at: '' })
    const store = useAuthStore()
    await store.login('a@b.com', 'pass')
    expect(localStorage.getItem('access_token')).toBe('tok123')
    expect(store.user?.email).toBe('a@b.com')
    expect(store.isAuthenticated).toBe(true)
  })

  it('logout clears token and user', () => {
    const store = useAuthStore()
    store.$patch({ user: { id: 1, email: 'a@b.com', created_at: '' } })
    localStorage.setItem('access_token', 'tok')
    store.logout()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('login throws on API error', async () => {
    vi.mocked(authApiModule.authApi.login).mockRejectedValue(new Error('401'))
    const store = useAuthStore()
    await expect(store.login('bad@b.com', 'wrong')).rejects.toThrow()
  })
})
```

- [ ] **Step 2: Run — confirm FAIL**

```bash
bun run test --run src/stores/__tests__/auth.spec.ts
```

Expected: `Cannot find module '../auth'`

- [ ] **Step 3: Write auth store**

```typescript
// frontend/src/stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserOut } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserOut | null>(null)
  const isAuthenticated = computed(() => user.value !== null)

  async function login(email: string, password: string) {
    const token = await authApi.login(email, password)
    localStorage.setItem('access_token', token.access_token)
    user.value = await authApi.me()
  }

  function logout() {
    localStorage.removeItem('access_token')
    user.value = null
  }

  async function restore() {
    const token = localStorage.getItem('access_token')
    if (!token) return
    try {
      user.value = await authApi.me()
    } catch {
      logout()
    }
  }

  return { user, isAuthenticated, login, logout, restore }
})
```

- [ ] **Step 4: Run — confirm PASS**

```bash
bun run test --run src/stores/__tests__/auth.spec.ts
```

Expected: `3 passed`

- [ ] **Step 5: Write LoginView.vue**

```vue
<!-- frontend/src/views/LoginView.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()
const authStore = useAuthStore()

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(email.value, password.value)
    router.push('/dashboard')
  } catch {
    error.value = 'Invalid email or password'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <h1>URL Shortener</h1>
      <form @submit.prevent="handleSubmit" data-testid="login-form">
        <div class="field">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" required autocomplete="email" />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input id="password" v-model="password" type="password" required autocomplete="current-password" />
        </div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f5f5f5; }
.login-card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
h1 { text-align: center; margin-bottom: 1.5rem; }
.field { margin-bottom: 1rem; }
.field label { display: block; margin-bottom: 0.25rem; font-weight: 500; }
.field input { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
button { width: 100%; padding: 0.75rem; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #dc2626; font-size: 0.875rem; margin-bottom: 0.5rem; }
</style>
```

- [ ] **Step 6: Write router/index.ts**

```typescript
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: () => import('../views/LoginView.vue') },
    {
      path: '/dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.isAuthenticated) {
    await auth.restore()
  }
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return '/login'
  }
})

export default router
```

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "feat: auth store, login view, route guards"
```

---

### Task 2.3: URL Store + Dashboard

**Files:**
- Create: `frontend/src/stores/urls.ts`
- Create: `frontend/src/components/CreateURLForm.vue`
- Create: `frontend/src/components/URLCard.vue`
- Create: `frontend/src/views/DashboardView.vue`
- Create: `frontend/src/stores/__tests__/urls.spec.ts`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/stores/__tests__/urls.spec.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useURLsStore } from '../urls'
import * as urlsApiModule from '../../api/urls'

vi.mock('../../api/urls', () => ({
  urlsApi: {
    list: vi.fn(),
    create: vi.fn(),
    remove: vi.fn(),
    stats: vi.fn(),
  },
}))

const mockURL = {
  id: 1, short_code: 'abc12345', original_url: 'https://ex.com', created_at: '', click_count: 0,
}

describe('urls store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchAll populates urls', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([mockURL])
    const store = useURLsStore()
    await store.fetchAll()
    expect(store.urls).toHaveLength(1)
    expect(store.urls[0].short_code).toBe('abc12345')
  })

  it('create prepends url to list', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([])
    vi.mocked(urlsApiModule.urlsApi.create).mockResolvedValue(mockURL)
    const store = useURLsStore()
    await store.fetchAll()
    await store.create('https://ex.com')
    expect(store.urls).toHaveLength(1)
  })

  it('remove filters url from list', async () => {
    vi.mocked(urlsApiModule.urlsApi.list).mockResolvedValue([mockURL])
    vi.mocked(urlsApiModule.urlsApi.remove).mockResolvedValue(undefined)
    const store = useURLsStore()
    await store.fetchAll()
    await store.remove(1)
    expect(store.urls).toHaveLength(0)
  })
})
```

- [ ] **Step 2: Run — confirm FAIL**

```bash
bun run test --run src/stores/__tests__/urls.spec.ts
```

Expected: `Cannot find module '../urls'`

- [ ] **Step 3: Write URL store**

```typescript
// frontend/src/stores/urls.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { urlsApi, type URLOut, type StatsOut } from '../api/urls'

export const useURLsStore = defineStore('urls', () => {
  const urls = ref<URLOut[]>([])
  const currentStats = ref<StatsOut | null>(null)

  async function fetchAll() {
    urls.value = await urlsApi.list()
  }

  async function create(originalUrl: string, customCode?: string) {
    const created = await urlsApi.create(originalUrl, customCode)
    urls.value.unshift(created)
    return created
  }

  async function remove(id: number) {
    await urlsApi.remove(id)
    urls.value = urls.value.filter((u) => u.id !== id)
  }

  async function fetchStats(id: number) {
    currentStats.value = await urlsApi.stats(id)
  }

  return { urls, currentStats, fetchAll, create, remove, fetchStats }
})
```

- [ ] **Step 4: Run — confirm PASS**

```bash
bun run test --run src/stores/__tests__/urls.spec.ts
```

Expected: `3 passed`

- [ ] **Step 5: Write CreateURLForm.vue**

```vue
<!-- frontend/src/components/CreateURLForm.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useURLsStore } from '../stores/urls'

const urlsStore = useURLsStore()
const originalUrl = ref('')
const customCode = ref('')
const error = ref('')
const loading = ref(false)

async function handleCreate() {
  error.value = ''
  loading.value = true
  try {
    await urlsStore.create(originalUrl.value, customCode.value || undefined)
    originalUrl.value = ''
    customCode.value = ''
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to create URL'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="create-form" @submit.prevent="handleCreate" data-testid="create-url-form">
    <h2>Shorten a URL</h2>
    <div class="field">
      <label for="original-url">Original URL</label>
      <input id="original-url" v-model="originalUrl" type="url" placeholder="https://example.com" required />
    </div>
    <div class="field">
      <label for="custom-code">Custom code (optional)</label>
      <input id="custom-code" v-model="customCode" type="text" placeholder="my-link" />
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button type="submit" :disabled="loading">{{ loading ? 'Creating…' : 'Create short URL' }}</button>
  </form>
</template>

<style scoped>
.create-form { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 2rem; }
h2 { margin-bottom: 1rem; }
.field { margin-bottom: 1rem; }
.field label { display: block; margin-bottom: 0.25rem; font-weight: 500; }
.field input { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
button { padding: 0.6rem 1.2rem; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; }
button:disabled { opacity: 0.6; }
.error { color: #dc2626; font-size: 0.875rem; }
</style>
```

- [ ] **Step 6: Write URLCard.vue**

```vue
<!-- frontend/src/components/URLCard.vue -->
<script setup lang="ts">
import type { URLOut } from '../api/urls'

const props = defineProps<{ url: URLOut; baseUrl: string }>()
const emit = defineEmits<{ delete: [id: number]; stats: [id: number] }>()

function copyShortUrl() {
  navigator.clipboard.writeText(`${props.baseUrl}/${props.url.short_code}`)
}
</script>

<template>
  <div class="url-card" :data-testid="`url-card-${url.id}`">
    <div class="url-info">
      <a :href="url.original_url" target="_blank" rel="noopener noreferrer" class="original">
        {{ url.original_url }}
      </a>
      <div class="short">
        <code>{{ baseUrl }}/{{ url.short_code }}</code>
        <button class="btn-copy" @click="copyShortUrl">Copy</button>
      </div>
      <span class="clicks">{{ url.click_count }} click{{ url.click_count !== 1 ? 's' : '' }}</span>
    </div>
    <div class="url-actions">
      <button class="btn-stats" @click="emit('stats', url.id)">Stats</button>
      <button class="btn-delete" @click="emit('delete', url.id)">Delete</button>
    </div>
  </div>
</template>

<style scoped>
.url-card { display: flex; justify-content: space-between; align-items: center; background: white; padding: 1rem 1.25rem; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 0.75rem; }
.url-info { flex: 1; min-width: 0; }
.original { display: block; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #1d4ed8; }
.short { display: flex; align-items: center; gap: 0.5rem; margin: 0.25rem 0; }
code { font-size: 0.875rem; color: #374151; }
.clicks { font-size: 0.8rem; color: #6b7280; }
.url-actions { display: flex; gap: 0.5rem; margin-left: 1rem; }
.btn-stats { padding: 0.4rem 0.8rem; border: 1px solid #3b82f6; background: transparent; color: #3b82f6; border-radius: 4px; cursor: pointer; }
.btn-delete { padding: 0.4rem 0.8rem; border: 1px solid #dc2626; background: transparent; color: #dc2626; border-radius: 4px; cursor: pointer; }
.btn-copy { font-size: 0.75rem; padding: 0.2rem 0.5rem; border: 1px solid #9ca3af; border-radius: 3px; cursor: pointer; background: transparent; }
</style>
```

- [ ] **Step 7: Write DashboardView.vue**

```vue
<!-- frontend/src/views/DashboardView.vue -->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useURLsStore } from '../stores/urls'
import CreateURLForm from '../components/CreateURLForm.vue'
import URLCard from '../components/URLCard.vue'

const authStore = useAuthStore()
const urlsStore = useURLsStore()
const selectedStats = ref<any>(null)
const statsError = ref('')
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

onMounted(() => urlsStore.fetchAll())

async function handleStats(id: number) {
  statsError.value = ''
  try {
    await urlsStore.fetchStats(id)
    selectedStats.value = urlsStore.currentStats
  } catch {
    statsError.value = 'Failed to load stats'
  }
}

async function handleDelete(id: number) {
  if (!confirm('Delete this URL?')) return
  await urlsStore.remove(id)
  if (selectedStats.value?.url_id === id) selectedStats.value = null
}
</script>

<template>
  <div class="dashboard">
    <header class="dash-header">
      <h1>URL Shortener</h1>
      <div class="user-info">
        <span>{{ authStore.user?.email }}</span>
        <button @click="authStore.logout()">Sign out</button>
      </div>
    </header>
    <main class="dash-content">
      <CreateURLForm />
      <section>
        <h2>Your URLs</h2>
        <p v-if="urlsStore.urls.length === 0" class="empty">No URLs yet. Create one above.</p>
        <URLCard
          v-for="url in urlsStore.urls"
          :key="url.id"
          :url="url"
          :base-url="BASE_URL"
          @stats="handleStats"
          @delete="handleDelete"
        />
      </section>
      <aside v-if="selectedStats" class="stats-panel">
        <h3>Stats for /{{ selectedStats.short_code }}</h3>
        <p><strong>Total clicks:</strong> {{ selectedStats.total_clicks }}</p>
        <table v-if="Object.keys(selectedStats.clicks_by_date).length">
          <thead><tr><th>Date</th><th>Clicks</th></tr></thead>
          <tbody>
            <tr v-for="(count, date) in selectedStats.clicks_by_date" :key="date">
              <td>{{ date }}</td><td>{{ count }}</td>
            </tr>
          </tbody>
        </table>
        <button @click="selectedStats = null">Close</button>
      </aside>
      <p v-if="statsError" class="error">{{ statsError }}</p>
    </main>
  </div>
</template>

<style scoped>
.dashboard { min-height: 100vh; background: #f9fafb; }
.dash-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 2rem; background: white; border-bottom: 1px solid #e5e7eb; }
.dash-header h1 { margin: 0; font-size: 1.25rem; }
.user-info { display: flex; align-items: center; gap: 1rem; }
.user-info button { padding: 0.4rem 0.8rem; border: 1px solid #e5e7eb; background: transparent; border-radius: 4px; cursor: pointer; }
.dash-content { max-width: 800px; margin: 0 auto; padding: 2rem 1rem; }
.empty { color: #6b7280; }
.stats-panel { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-top: 2rem; }
.stats-panel table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
.stats-panel th, .stats-panel td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #e5e7eb; }
.error { color: #dc2626; }
</style>
```

- [ ] **Step 8: Run all frontend tests**

```bash
bun run test --run
```

Expected: `6 passed`

- [ ] **Step 9: Commit**

```bash
git add .
git commit -m "feat: URL store, dashboard, URLCard, CreateURLForm, stats panel"
```

---

### Task 2.4: Frontend Dockerfile

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `frontend/.env.production`
- Create: `frontend/.dockerignore`

- [ ] **Step 1: Write .env.production**

```
VITE_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 2: Write Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM oven/bun:1 AS builder
WORKDIR /app
COPY package.json bun.lockb* ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 3: Write nginx.conf**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

- [ ] **Step 4: Write .dockerignore**

```
node_modules/
dist/
.env.local
```

- [ ] **Step 5: Build smoke-test**

```bash
docker build -t url-shortener-frontend ./frontend
echo "frontend build OK"
```

Expected: `frontend build OK`

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "chore: frontend Dockerfile with nginx"
```

---

### Task 2.5: Merge Frontend to Develop

- [ ] **Step 1: Final test run**

```bash
bun run test --run
```

Expected: all pass

- [ ] **Step 2: Merge**

```bash
cd /Users/miohitokiri5474/project/url-shortener-fullstack
git merge feature/frontend --no-ff -m "feat: merge frontend — Vue3, auth, URL CRUD, stats, Docker"
```

- [ ] **Step 3: Remove worktree**

```bash
git worktree remove ../url-shortener-frontend
```

---

## Phase 3: Docker Integration

### Task 3.1: docker-compose

**Files:**
- Create: `docker-compose.yml`
- Create: `docker-compose.override.yml`

- [ ] **Step 1: Write docker-compose.yml**

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
      - DATABASE_URL=sqlite+aiosqlite:///./data/shortener.db
    volumes:
      - backend-data:/app/data
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  backend-data:
```

- [ ] **Step 2: Write docker-compose.override.yml**

```yaml
version: "3.9"

services:
  backend:
    command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend/src:/app/src

  frontend:
    build:
      target: builder
    command: bun run dev --host 0.0.0.0
    ports:
      - "5173:5173"
```

- [ ] **Step 3: Integration smoke-test**

```bash
docker-compose up --build -d
sleep 8
curl -sf http://localhost:8000/docs > /dev/null && echo "backend OK" || echo "backend FAIL"
curl -sf http://localhost:80 > /dev/null && echo "frontend OK" || echo "frontend FAIL"
docker-compose down
```

Expected: `backend OK` and `frontend OK`

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml docker-compose.override.yml
git commit -m "chore: docker-compose orchestration for full stack"
```

---

### Task 3.2: Merge Develop → Main

- [ ] **Step 1: Run all backend tests on develop**

```bash
cd backend && uv run pytest -v
```

Expected: all pass

- [ ] **Step 2: Run all frontend tests on develop**

```bash
cd ../frontend && bun run test --run
```

Expected: all pass

- [ ] **Step 3: Merge develop → main and tag**

```bash
cd /Users/miohitokiri5474/project/url-shortener-fullstack
git checkout main
git merge develop --no-ff -m "release: v1.0.0 — URL shortener fullstack"
git tag v1.0.0
```

- [ ] **Step 4: Verify**

```bash
git log --oneline -8
git tag
```

Expected: `v1.0.0` in tag list, clean merge commit on main

---

## Git Branch Strategy

```
main          ← stable releases only, tagged
  └── develop ← integration branch
        ├── feature/backend  (worktree: ../url-shortener-backend)
        └── feature/frontend (worktree: ../url-shortener-frontend)
```

Merge order: feature/* → develop → main
