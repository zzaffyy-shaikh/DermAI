"""FastAPI application entrypoint.

Run from the backend/ directory:
    uvicorn app.main:app --reload
Docs at http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import init_db
from .api import routes_auth, routes_history, routes_profile, routes_report

# On Windows, mimetypes can map .js to text/plain (from the registry), which breaks
# native ES-module loading. Force the correct types so the web app loads.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"
WEBAPP_DIR = BASE_DIR / "webapp"
from .ml.classifier import SkinClassifier
from .ml.segmentation import LesionSegmenter
from .api import routes_admin, routes_chat, routes_consult, routes_diagnose, routes_notify


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise the database (create tables + seed admin) before serving.
    settings = get_settings()
    print(f"[startup] initialising database at {settings.database_url} ...")
    init_db()

    # Warm the models once at startup so the first request isn't slow.
    print(f"[startup] loading ConvNeXt model from {settings.model_path} ...")
    clf = SkinClassifier.get()
    print(f"[startup] classifier ready on {clf.device}; classes={clf.classes}")
    seg = LesionSegmenter.get()
    print(f"[startup] MobileSAM available: {seg.available}")
    print(f"[startup] LLM provider: {settings.llm_provider} | auth mode: {settings.auth_mode}")
    if settings.auth_mode == "dev":
        print("[security] WARNING: dev auth is ON — X-Role/X-User-Id headers are trusted. "
              "Set DERMAI_AUTH_MODE to something other than 'dev' in production.")
    if settings.seed_admin_password == "admin123":
        print("[security] WARNING: default admin password in use — set DERMAI_SEED_ADMIN_PASSWORD.")
    if "*" in settings.cors_origins:
        print("[security] NOTE: CORS allows all origins — restrict DERMAI_CORS_ORIGINS in production.")
    yield
    print("[shutdown] bye")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DermAI API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,   # we authenticate with bearer tokens, not cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def no_cache_spa(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith("/app") or path.startswith("/ui"):
            response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/app/")

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    app.include_router(routes_auth.router)
    app.include_router(routes_diagnose.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_consult.router)
    app.include_router(routes_notify.router)
    app.include_router(routes_admin.router)
    app.include_router(routes_history.router)
    app.include_router(routes_report.router)
    app.include_router(routes_profile.router)

    # Static frontends, mounted last so they don't shadow the API routes above.
    #   /app -> the full web application (login + role dashboards)
    #   /ui  -> the lightweight test console
    if WEBAPP_DIR.exists():
        app.mount("/app", StaticFiles(directory=WEBAPP_DIR, html=True), name="webapp")
    if STATIC_DIR.exists():
        app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
    return app


app = create_app()
