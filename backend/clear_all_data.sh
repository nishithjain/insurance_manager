#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
unset PYTHONHOME EM_PYTHON_HOME BM_PYTHON_HOME 2>/dev/null || true
cd "$DIR"
PY="$(bash "$DIR/print_venv_python.sh" 2>/dev/null)" || {
  echo "No .venv found. From repo root: ./recreate_venv.sh" >&2
  exit 1
}
exec "$PY" clear_all_data.py "$@"
