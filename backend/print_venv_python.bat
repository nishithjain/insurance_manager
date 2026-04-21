@echo off
setlocal EnableDelayedExpansion
set "SCRIPT=%~dp0"
set "SCRIPT=%SCRIPT:~0,-1%"
set "REPO=%SCRIPT%\.."
if exist "%REPO%\.venv\Scripts\python.exe" (
  for %%I in ("%REPO%\.venv\Scripts\python.exe") do echo %%~fI
  exit /b 0
)
if exist "%SCRIPT%\.venv\Scripts\python.exe" (
  for %%I in ("%SCRIPT%\.venv\Scripts\python.exe") do echo %%~fI
  exit /b 0
)
exit /b 1
