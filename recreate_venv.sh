#!/usr/bin/env bash
# Create repo-root .venv using Python from PATH (python.org / Store), or optional legacy BMC.
# Optional: export PYTHON_FOR_VENV="/c/path/to/python.exe"
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Old BMC installs often set PYTHONHOME in the shell/profile. If set, venv copies launchers from
# that tree (wrong Python) → WinError 2. Clear for this script and for child processes.
unset PYTHONHOME EM_PYTHON_HOME BM_PYTHON_HOME PYTHONPATH 2>/dev/null || true

pick_python() {
  if [ -n "${PYTHON_FOR_VENV:-}" ] && [ -f "$PYTHON_FOR_VENV" ]; then
    printf '%s' "$PYTHON_FOR_VENV"
    return 0
  fi
  if command -v py >/dev/null 2>&1; then
    if PY="$(py -3 -c "import sys; print(sys.executable)" 2>/dev/null)" && [ -f "$PY" ]; then
      printf '%s' "$PY"
      return 0
    fi
  fi
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
      printf '%s' "$(command -v "$c")"
      return 0
    fi
  done
  if [ -n "${BM_PYTHON_HOME:-}" ] && [ -f "$BM_PYTHON_HOME/python.exe" ]; then
    printf '%s' "$BM_PYTHON_HOME/python.exe"
    return 0
  fi
  return 1
}

if ! PY="$(pick_python)"; then
  echo "Could not find Python 3. Install from https://www.python.org/downloads/windows/ and check 'Add to PATH'," >&2
  echo "or set PYTHON_FOR_VENV to the full path to python.exe" >&2
  exit 1
fi

echo "Using: $PY"
PYTHONHOME= EM_PYTHON_HOME= BM_PYTHON_HOME= "$PY" --version
rm -rf .venv
# Empty env vars so venv uses THIS Python's Lib\venv\scripts, not a stale PYTHONHOME.
PYTHONHOME= EM_PYTHON_HOME= BM_PYTHON_HOME= "$PY" -m venv .venv
PYTHONHOME= EM_PYTHON_HOME= BM_PYTHON_HOME= .venv/Scripts/python.exe -m pip install --upgrade pip
if [ -f backend/requirements.txt ]; then
  PYTHONHOME= EM_PYTHON_HOME= BM_PYTHON_HOME= .venv/Scripts/python.exe -m pip install -r backend/requirements.txt
fi
echo "OK: .venv/Scripts/python.exe — run ./run_backend.sh to start the API"
