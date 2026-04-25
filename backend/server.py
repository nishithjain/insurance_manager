"""
Application entry point.

Thin composition root: loads env, creates the FastAPI app with a lifespan,
mounts the ``/api`` router group from :mod:`routers`, and configures CORS.

All endpoint logic lives in ``routers/`` modules; all SQL helpers in
``repositories/``; all Pydantic models in :mod:`schemas`; and all domain
rules / constants in :mod:`domain`.
"""

from __future__ import annotations

import logging
import os
import json
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware

from database import init_db
from deps import get_current_principal
from routers import (
    app_users,
    auth,
    customers,
    exports,
    policies,
    renewals,
    settings,
    statements,
    sync,
    system,
)


ROOT_DIR = Path(__file__).parent
APP_DIR = ROOT_DIR.parent
SERVICE_CONFIG_PATH = APP_DIR / "config" / "backend_service_config.json"
# ``override=True`` ensures local ``backend/.env`` values win over inherited
# empty/system env vars (common on Windows shells), avoiding false
# "Authentication is not configured" errors.
load_dotenv(ROOT_DIR / ".env", override=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _service_config() -> dict:
    """Read optional installer/service config without making dev startup depend on it."""
    if not SERVICE_CONFIG_PATH.exists():
        return {}
    try:
        with SERVICE_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            return json.load(config_file)
    except Exception as exc:
        logger.warning("Could not read %s: %s", SERVICE_CONFIG_PATH, exc)
        return {}


def _resolve_frontend_dist() -> Path | None:
    """Resolve the production frontend folder for installed service mode."""
    config = _service_config()
    if config.get("frontend_enabled", True) is False:
        logger.info("Frontend static serving is disabled by config.")
        return None

    raw_path = (
        os.environ.get("FRONTEND_DIST_PATH")
        or config.get("frontend_dist_path")
        or "frontend_dist"
    )
    frontend_path = Path(str(raw_path))
    if not frontend_path.is_absolute():
        frontend_path = APP_DIR / frontend_path
    return frontend_path.resolve()


FRONTEND_DIST = _resolve_frontend_dist()
FRONTEND_INDEX = FRONTEND_DIST / "index.html" if FRONTEND_DIST else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the DB on startup; log on shutdown."""
    await init_db()
    logger.info("Application started")
    try:
        yield
    finally:
        logger.info("Application shutdown")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def site_root():
    """Open the installed React UI when present; otherwise show the API landing."""
    if FRONTEND_INDEX and FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return {
        "message": "Insurance App API",
        "api_base": "/api/",
        "health": "/api/health",
        "docs": "/docs",
    }


# Router topology:
#   /api                       → public (system + auth).
#   /api (authenticated)       → every business router; a single route-level
#                                 dependency enforces a valid JWT so no handler
#                                 can forget the guard.
#   /api/users (admin-only)    → enforced inside routers/app_users.py via
#                                 ``require_admin`` per handler.
api_public = APIRouter(prefix="/api")
api_public.include_router(system.router)
api_public.include_router(auth.router)

api_protected = APIRouter(prefix="/api", dependencies=[Depends(get_current_principal)])
api_protected.include_router(customers.router)
api_protected.include_router(policies.router)
api_protected.include_router(renewals.router)
api_protected.include_router(settings.router)
api_protected.include_router(statements.router)
api_protected.include_router(exports.router)
api_protected.include_router(sync.router)
api_protected.include_router(app_users.router)

app.include_router(api_public)
app.include_router(api_protected)


# CORS: explicit origins in .env (use "*" only if you accept allow_credentials=False).
_cors_raw = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
).strip()
if _cors_raw == "*":
    _cors_origins = ["*"]
    _cors_credentials = False
else:
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
    _cors_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_credentials=_cors_credentials,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


if FRONTEND_DIST and FRONTEND_INDEX and FRONTEND_INDEX.exists():
    logger.info("Serving frontend static files from %s", FRONTEND_DIST)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve built React files and fall back to index.html for SPA routes."""
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json")):
            raise HTTPException(status_code=404)

        requested_path = (FRONTEND_DIST / full_path).resolve()
        try:
            requested_path.relative_to(FRONTEND_DIST)
        except ValueError:
            raise HTTPException(status_code=404) from None

        if requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(FRONTEND_INDEX)
else:
    logger.warning(
        "Frontend build not found; API-only mode. Expected index at %s",
        FRONTEND_INDEX,
    )
