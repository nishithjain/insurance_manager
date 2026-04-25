@echo off
setlocal
REM API server: repo-root .venv only (no BMC PYTHONHOME).
set "REPO_ROOT=%~dp0.."
pushd "%REPO_ROOT%"
if not exist ".venv\Scripts\python.exe" (
  echo No .venv found. Run scripts\recreate_venv.bat from the repo root first.
  exit /b 1
)
cd backend
"..\.venv\Scripts\python.exe" -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
popd
