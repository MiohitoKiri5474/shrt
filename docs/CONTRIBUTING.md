# Contributing

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (backend Python env/dependency manager)
- [Bun](https://bun.sh/) 1.3.x (frontend package manager/test runner)
- Docker + Docker Compose (for running the full stack)

## Setup

```bash
# Backend
cd backend
uv sync --all-groups

# Frontend
cd frontend
bun install
```

Environment variables: see [SETUP.md](SETUP.md) and copy `.env.example` → `.env` (root, production Compose) and `frontend/.env.example` → `frontend/.env` (dev).

<!-- AUTO-GENERATED: scripts table -->
## Available commands

### Frontend (`frontend/`, run via `bun run <script>`)

| Command | Description |
|---|---|
| `bun run dev` | Start the Vite dev server with hot reload |
| `bun run build` | Type-check (`vue-tsc --build`) then production build |
| `bun run preview` | Preview the production build locally |
| `bun run test:unit` | Run the Vitest unit/component test suite |
| `bun run type-check` | Type-check only (`vue-tsc --build`) |
| `bun run lint` | Run `oxlint --fix` then `eslint --fix --cache` |

### Backend (`backend/`, run via `uv run <command>`)

| Command | Description |
|---|---|
| `uv run uvicorn app.main:app --reload` | Start the API with hot reload (needs `PYTHONPATH=src` or run from `backend/src`) |
| `uv run pytest --cov --cov-report=term-missing --cov-fail-under=80` | Run the test suite with coverage, matching CI |

### Docker Compose (repo root)

| Command | Description |
|---|---|
| `docker compose up --build` | Production-mode stack: redis, backend, frontend (nginx) |
| `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` | Adds backend hot-reload + `APP_ENV=development` |
<!-- /AUTO-GENERATED -->

## Testing

- **Backend**: pytest, `backend/tests/`. Coverage gate is 80% (`--cov-fail-under=80`), enforced in CI (`.github/workflows/test.yml`).
- **Frontend**: Vitest, colocated in `__tests__/` next to the code under test. CI runs type-check, lint, and `bun run test:unit --run`.
- Both suites must pass before merging — see `.github/workflows/test.yml` for the exact commands CI runs.

## Code style

- **Frontend**: ESLint (`eslint.config.ts`) + oxlint, run via `bun run lint`. No Prettier config in this repo — don't add formatting-only diffs unless you also wire up a formatter project-wide.
- **Backend**: no linter/formatter is configured in CI or `pyproject.toml` today. Follow the existing style in `backend/src/app/` (type hints on function signatures, async I/O throughout) rather than introducing a new tool unasked.
- There are no git hooks / pre-commit config in this repo — checks run in CI, not locally on commit.

## Branching & PRs

This repo uses a worktree-per-branch workflow — see the root [CLAUDE.md](../CLAUDE.md) for the exact `git worktree add` commands.

- Branch base: `develop`. Branch names: `feature/xxx` or `fix/xxx`.
- Merge order: `feature/xxx`/`fix/xxx` → `develop` → `main`. Never commit directly to `main` or `develop`.

### PR checklist

- [ ] Branch is based on `develop`, named `feature/xxx` or `fix/xxx`
- [ ] `bun run type-check`, `bun run lint`, `bun run test:unit --run` pass (frontend changes)
- [ ] `uv run pytest --cov --cov-fail-under=80` passes (backend changes)
- [ ] New/changed endpoints are reflected in [API.md](API.md)
- [ ] New/changed env vars are reflected in [SETUP.md](SETUP.md) and `.env.example`
- [ ] Security-sensitive changes (auth, input handling, SSRF, rate limits) checked against [SECURITY.md](../SECURITY.md)
- [ ] CI is green on the PR
