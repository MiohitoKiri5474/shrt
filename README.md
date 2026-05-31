# URL Shortener

Fullstack URL shortener — Vue3 frontend, FastAPI backend, Docker.

## Quick Start

### Production

**Required environment variables** — create a `.env` file before starting (copy `.env.example` as a starting point):

```bash
cp .env.example .env
# Then set SECRET_KEY, DATABASE_URL (PostgreSQL), CORS_ALLOWED_ORIGINS, and admin credentials
```

Key required vars:
- `SECRET_KEY` — random hex string (`python3 -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL` — PostgreSQL connection string (`postgresql+asyncpg://user:pass@host:5432/db`)
- `CORS_ALLOWED_ORIGINS` — comma-separated allowed origins (`https://yourdomain.com`)
- `DEFAULT_USER_EMAIL` / `DEFAULT_USER_PASSWORD` — seed admin credentials (password min 12 chars)

```bash
docker compose up --build
```

### Development

Development config is kept in `docker-compose.dev.yml` and must be passed explicitly (it is no longer auto-loaded):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Frontend: http://localhost:80
Backend API: http://localhost:8000/docs
