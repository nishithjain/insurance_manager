#!/usr/bin/env bash
# Import CSV into statement_policy_lines, then materialize customers/policies for dev user.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
unset PYTHONHOME EM_PYTHON_HOME BM_PYTHON_HOME 2>/dev/null || true
REPO_ROOT="$(cd "$DIR/.." && pwd)"

PY="$(bash "$DIR/print_venv_python.sh" 2>/dev/null)" || {
  echo "No Python virtualenv found (looked for .venv under repo root or backend/)." >&2
  echo "" >&2
  echo "Create one from the repository root ($REPO_ROOT):" >&2
  echo "  ./recreate_venv.sh" >&2
  echo "" >&2
  echo "Or, if you have Python 3.10+ on PATH:" >&2
  echo "  cd \"$REPO_ROOT\"" >&2
  echo "  python -m venv .venv" >&2
  echo "  .venv/Scripts/python.exe -m pip install -r backend/requirements.txt" >&2
  echo "" >&2
  echo "If you use BMC Python, set BM_PYTHON_HOME and run ./recreate_venv.sh (see recreate_venv.sh)." >&2
  exit 1
}

echo "==> Python: $PY"
echo "==> Database file: $($PY -c "from db_path import DB_PATH; print(DB_PATH.resolve())")"
"$PY" import_march_statements.py "../MARCH STATEMENTS 2026.csv" || "$PY" import_march_statements.py "MARCH STATEMENTS 2026.csv"
"$PY" materialize_from_statements.py --user-id user_dev_local || {
  echo "If materialize failed: sign in once with Local dev login, then run:"
  echo "  $PY materialize_from_statements.py --list-users"
  echo "  $PY materialize_from_statements.py --user-id YOUR_USER_ID"
  exit 1
}
echo "==> Done. Check: curl -s http://127.0.0.1:8000/api/health"
echo "    Dev login in the app uses user_dev_local; Google users need --user-id from --list-users."
