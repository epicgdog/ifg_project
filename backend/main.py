"""FastAPI entrypoint for the ForgeReach backend."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import config as config_routes
from .routes import run as run_routes
from .routes import samples as samples_routes
from .routes import webhooks as webhook_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure working directories exist before serving requests.
    Path("out").mkdir(parents=True, exist_ok=True)
    Path(".cache").mkdir(parents=True, exist_ok=True)
    Path("backend/uploads").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="ForgeReach API", version="1.0.0", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(config_routes.router)
app.include_router(run_routes.router)
app.include_router(samples_routes.router)
app.include_router(webhook_routes.router)
