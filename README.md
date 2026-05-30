# URL Shortener

Fullstack URL shortener — Vue3 frontend, FastAPI backend, Docker.

## Quick Start

### Production

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
