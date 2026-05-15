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
async def startup():  # pragma: no cover
    await create_tables()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(urls.router, prefix="/api/urls", tags=["urls"])
app.include_router(redirect.router, tags=["redirect"])
