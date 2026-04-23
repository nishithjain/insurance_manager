"""
Domain layer: pure business rules and types.

Nothing in this package may import from FastAPI, aiosqlite, or HTTP layers. Keeping it
framework-free makes it trivially unit-testable and safe to reuse from CLI scripts.
"""
