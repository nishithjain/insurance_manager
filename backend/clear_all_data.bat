@echo off
cd /d "%~dp0"
set "PYTHONHOME="
set "EM_PYTHON_HOME="
if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" clear_all_data.py %*
) else (
  python clear_all_data.py %*
)
