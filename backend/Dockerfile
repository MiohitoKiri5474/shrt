FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/

ENV PYTHONPATH=/app/src
ENV DATABASE_URL=sqlite+aiosqlite:///./data/shortener.db

RUN mkdir -p /app/data

RUN adduser --system --no-create-home --uid 10001 appuser \
    && chown -R appuser /app/data
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
