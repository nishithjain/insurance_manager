@echo off
REM Import CSV without PYTHONHOME (setting it breaks some venvs / encodings).
cd /d "%~dp0"
set "PYTHONHOME="
set "EM_PYTHON_HOME="
if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" import_march_statements.py %*
) else (
  python import_march_statements.py %*
)
