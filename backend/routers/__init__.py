"""
HTTP routers split by resource.

Each module defines its own :class:`~fastapi.APIRouter` with no prefix; the shared
``/api`` prefix is applied centrally in :mod:`server` when including each router.
"""
