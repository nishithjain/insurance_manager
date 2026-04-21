#!/usr/bin/env bash
# Start API: backend/server.py with repo-root .venv (standard python.org install — no PYTHONHOME).
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="$ROOT/.venv/Scripts/python.exe"
if [ ! -f "$PY" ]; then
  echo "No venv at $PY — from repo root run: ./recreate_venv.sh" >&2
  exit 1
fi
cd "$ROOT/backend" && exec "$PY" -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
