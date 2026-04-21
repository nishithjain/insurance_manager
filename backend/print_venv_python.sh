#!/usr/bin/env bash
# Print absolute path to the project venv Python, or exit 1.
# Tries: repo/.venv (Windows + Unix), backend/.venv
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
for p in \
  "$REPO/.venv/Scripts/python.exe" \
  "$REPO/.venv/bin/python3" \
  "$REPO/.venv/bin/python" \
  "$HERE/.venv/Scripts/python.exe" \
  "$HERE/.venv/bin/python3" \
  "$HERE/.venv/bin/python"
do
  if [ -f "$p" ]; then
    printf '%s\n' "$p"
    exit 0
  fi
done
exit 1
