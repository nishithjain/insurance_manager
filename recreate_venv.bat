@echo off
setlocal
cd /d "%~dp0"

REM Stale PYTHONHOME (e.g. from old BMC) makes venv copy launchers from the wrong install — clear it.
set "PYTHONHOME="
set "EM_PYTHON_HOME="
set "BM_PYTHON_HOME="
set "PYTHONPATH="

REM Prefer: py -3, then python on PATH. Optional: set PYTHON_FOR_VENV=C:\Path\to\python.exe
REM Legacy BMC: set BM_PYTHON_HOME=...

if defined PYTHON_FOR_VENV (
  set "PY=%PYTHON_FOR_VENV%"
  goto havepy
)
if defined BM_PYTHON_HOME if exist "%BM_PYTHON_HOME%\python.exe" (
  set "PY=%BM_PYTHON_HOME%\python.exe"
  goto havepy
)
where py >nul 2>&1
if %errorlevel%==0 (
  for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%i"
)
if not defined PY set "PY=python"

:havepy
"%PY%" --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3 from https://www.python.org/downloads/windows/ ^(check Add to PATH^) or set PYTHON_FOR_VENV
  exit /b 1
)
echo Using "%PY%"
"%PY%" --version
rmdir /s /q .venv 2>nul
"%PY%" -m venv .venv
if errorlevel 1 exit /b 1
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if exist backend\requirements.txt pip install -r backend\requirements.txt
echo OK: run run_backend.bat to start the API
