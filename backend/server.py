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
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI
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
    statements,
    sync,
    system,
)


ROOT_DIR = Path(__file__).parent
# ``override=True`` ensures local ``backend/.env`` values win over inherited
# empty/system env vars (common on Windows shells), avoiding false
# "Authentication is not configured" errors.
load_dotenv(ROOT_DIR / ".env", override=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
    """So opening http://host:port/ in a browser is not a 404; API lives under /api."""
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
