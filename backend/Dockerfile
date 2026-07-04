# python:3.12-slim, digest resolved 2026-07-04
FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf

WORKDIR /app

RUN pip install uv==0.11.26

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/

ENV PYTHONPATH=/app/src \
    UV_NO_CACHE=1

RUN mkdir -p /app/data

RUN adduser --system --no-create-home --uid 10001 appuser \
    && chown -R appuser /app/data
USER appuser

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
