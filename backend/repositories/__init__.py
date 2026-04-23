"""
Data-access helpers shared by router modules.

Kept deliberately thin for now: these re-export SQL fragments and row→model mappers
that used to live as module-private helpers in ``server.py``. A fuller repository
refactor (with per-entity classes) is a future step; this package is the seam we
need right now to deduplicate SQL across the route split.
"""
