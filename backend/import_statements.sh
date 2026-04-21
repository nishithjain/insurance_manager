#!/usr/bin/env bash
# Import CSV; clear PYTHONHOME so encodings/stdlib resolve (Git Bash / MSYS).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
unset PYTHONHOME EM_PYTHON_HOME BM_PYTHON_HOME 2>/dev/null || true
cd "$DIR"
PY="$(bash "$DIR/print_venv_python.sh" 2>/dev/null)" || {
  echo "No .venv found. From repo root run: ./recreate_venv.sh  (or: python -m venv .venv && .venv/Scripts/python.exe -m pip install -r backend/requirements.txt)" >&2
  exit 1
}
exec "$PY" import_march_statements.py "$@"
