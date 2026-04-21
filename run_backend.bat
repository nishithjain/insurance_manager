@echo off
REM API server: repo-root .venv only (no BMC PYTHONHOME).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo No .venv — run recreate_venv.bat from repo root first.
  exit /b 1
)
cd backend
"..\.venv\Scripts\python.exe" -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
