# python:3.14-slim (tag bumped from 3.12-slim by dependabot PR #335), digest refreshed 2026-08-14 by PR #390
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

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
