# Architecture

## Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + TypeScript, Vite, Pinia, vue-router, Axios |
| Backend | FastAPI (async), SQLAlchemy (async), Pydantic v2 |
| Auth | JWT (HS256) in an HttpOnly, SameSite=Strict cookie |
| Rate limiting | SlowAPI, backed by Redis (falls back to in-memory if `REDIS_URL` unset) |
| Database | PostgreSQL in production; SQLite allowed only when `APP_ENV=development` |
| Reverse proxy | Nginx (serves the built frontend, proxies `/api/*` to backend) |
| Orchestration | Docker Compose (`redis`, `backend`, `frontend` services) |

## Request flow

```
Browser
  │
  ▼
Nginx (frontend container, port 80)
  ├── /api/*        → proxy → backend:8000
  ├── /login, /dashboard, /  → index.html (SPA)
  └── /{short_code} → tries static file, falls back to backend:8000 (redirect lookup)
  │
  ▼
FastAPI (backend container, port 8000, internal-only)
  ├── SecurityHeadersMiddleware (CSP, X-Frame-Options, etc.)
  ├── CORSMiddleware
  ├── SlowAPI rate limiter (per-route limits, keyed by real client IP)
  └── routers: auth, urls, redirect
  │
  ▼
PostgreSQL/SQLite (via SQLAlchemy async engine)
Redis (rate-limit counters only — no persistence, no app data)
```

## Backend layout

```
backend/src/app/
├── main.py              # FastAPI app, middleware, startup seeding, router registration
├── config.py            # env var validation (SECRET_KEY, DATABASE_URL, REDIS_URL checks)
├── database.py          # async engine/session, create_tables(), ad-hoc schema migration
├── models.py             # SQLAlchemy models: User, URL, Click
├── schemas.py            # Pydantic request/response schemas + SSRF validation
├── rate_limiter.py        # SlowAPI limiter, trusted-proxy-aware real-IP resolution
├── utils.py               # IP anonymization for GDPR/CCPA-compliant click logging
├── routers/
│   ├── auth.py            # register/login/logout/me/users, get_current_user dependency
│   ├── urls.py             # create/list/delete URLs, stats
│   └── redirect.py         # GET /{short_code} → 302 redirect + click logging
└── services/
    └── auth.py             # password hashing, JWT issuance/decoding, short-code generation
```

There is no Alembic. Tables are created with `Base.metadata.create_all()` on startup, and `database.py::_migrate_schema()` hand-rolls additive column migrations (adding `is_admin`/`username`, widening `original_url`) for both SQLite and PostgreSQL dialects.

## Frontend layout

```
frontend/src/
├── main.ts                # app entrypoint
├── App.vue                 # root component, initializes theme store, renders RouterView
├── router/index.ts          # routes + auth guard
├── stores/                  # Pinia stores: auth, urls, theme
├── api/                      # client.ts (Axios instance), auth.ts, urls.ts
├── views/                     # LoginView.vue, DashboardView.vue
└── components/                 # CreateURLForm.vue, URLCard.vue, AddUserForm.vue, icons/
```

`components/HelloWorld.vue`, `TheWelcome.vue`, `WelcomeItem.vue`, and `stores/counter.ts` are unmodified Vite/Vue scaffold leftovers — not imported by `App.vue` or any route, safe to ignore or delete.

### Routing & auth guard

- `/` redirects to `/dashboard`.
- `/login` — public.
- `/dashboard` — `meta.requiresAuth: true`; the global `beforeEach` guard calls `auth.restore()` (`GET /api/auth/me`) to re-establish session state from the cookie on load, and redirects to `/login` if still unauthenticated.

### State (Pinia)

- **auth store** — `user`, `isAuthenticated`; `login`, `logout`, `restore`, `updateUsername`.
- **urls store** — `urls`, `currentStats`; `fetchAll`, `create`, `remove`, `fetchStats`.
- **theme store** — `isDark` (persisted to `localStorage`, toggles a `dark` class on `<html>`).

### API client

`src/api/client.ts` creates an Axios instance with `withCredentials: true` (so the HttpOnly auth cookie is sent) and `baseURL` from `VITE_API_BASE_URL` (empty by default — same-origin, proxied by nginx). A response interceptor redirects to `/login` on `401`.

## Security model

See [SECURITY.md](../SECURITY.md) for the full writeup of CSRF strategy, JWT lifecycle tradeoffs, and password policy. Key mechanisms not covered there:

- **SSRF prevention** (`schemas.py::validate_no_ssrf`) — resolves the hostname via `socket.getaddrinfo()` and blocks private/loopback/link-local/reserved/multicast destinations. Runs both at URL-creation time and at redirect time (to catch DNS rebinding between creation and click).
- **IP anonymization** (`utils.py::anonymize_ip`) — click logs store IPv4 with the last octet zeroed and IPv6 with only the first /48 retained.
- **Real-IP resolution for rate limiting** (`rate_limiter.py::get_real_ip`) — only trusts `X-Forwarded-For` when the direct connection comes from an address in `TRUSTED_PROXY_CIDRS`/`TRUSTED_PROXY_IPS`; otherwise an attacker could forge the header to dodge per-IP limits.
- **Timing-attack mitigation on login** — unknown users and over-length passwords run dummy bcrypt operations so response time doesn't leak which failure case occurred.
