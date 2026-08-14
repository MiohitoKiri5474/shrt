# python:3.14-slim (tag bumped from 3.12-slim by dependabot PR #335), digest refreshed 2026-08-14 by PR #390
FROM python:3.14-slim@sha256:a7fb1e634c4a578f9e0bd6327f11a3cde11b7a9395f48e24360c0988bcc5c2bc

WORKDIR /app

RUN pip install uv==0.11.26

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/

ENV PYTHONPATH=/app/src \
    UV_NO_CACHE=1

RUN mkdir -p /app/data

RUN adduser --system --no-create-home --uid 10001 appuser \
    && chown -R appuser /app/data
USER appuser

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
