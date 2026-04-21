#!/usr/bin/env bash
# Run uvicorn from backend/ using repo .venv or backend/.venv (no PYTHONHOME — standard Python).
cd "$(dirname "$0")"
unset PYTHONHOME EM_PYTHON_HOME BM_PYTHON_HOME 2>/dev/null || true
if [ -f "../.venv/Scripts/python.exe" ]; then
  PY="../.venv/Scripts/python.exe"
elif [ -f ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
else
  echo "No .venv found. From repo root: ../recreate_venv.sh" >&2
  exit 1
fi
exec "$PY" -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
