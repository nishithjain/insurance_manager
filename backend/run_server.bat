@echo off
REM Run from backend folder so "server" imports. Venv may be ..\ .venv (repo root) or .venv here.
cd /d "%~dp0"
if not defined BM_PYTHON_HOME set "BM_PYTHON_HOME=C:\Users\nrajanna\Git-projects\bmcpython\bmcpython_V7"
set "PYTHONHOME=%BM_PYTHON_HOME%"
set "EM_PYTHON_HOME=%BM_PYTHON_HOME%"

if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
) else if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
) else (
  python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
)
