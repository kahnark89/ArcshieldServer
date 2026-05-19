from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os

from app.config import get_settings
from app.routers import events, twin, config, media
from app.services.embedding import embedding_service
from app.tasks.threshold_recalc import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    try:
        embedding_service.load()
    except Exception as e:
        print(f"Warning: embedding model failed to load ({e}). RAG will use text fallback.")
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="arcshield-corpus",
    version="0.1.0",
    description="Event corpus and RAG server for ArcShield",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    settings = get_settings()
    path = request.url.path
    # Skip auth for dashboard, docs, openapi spec, and health
    if (
        path.startswith("/dashboard")
        or path.startswith("/docs")
        or path.startswith("/openapi")
        or path == "/health"
        or path == "/"
    ):
        return await call_next(request)

    key = request.headers.get("X-API-Key")
    if key != settings.api_key:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

    return await call_next(request)


app.include_router(events.router)
app.include_router(twin.router)
app.include_router(config.router)
app.include_router(media.router)

dashboard_dist = os.path.join(os.path.dirname(__file__), "..", "dashboard", "dist")
if os.path.isdir(dashboard_dist):
    app.mount("/dashboard", StaticFiles(directory=dashboard_dist, html=True), name="dashboard")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"service": "arcshield-corpus", "docs": "/docs", "dashboard": "/dashboard"}
