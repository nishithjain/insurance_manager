@echo off
REM Fixes damaged lockfile + stuck node_modules on Windows (OneDrive/AV locks).
REM 1) Close Cursor/VS Code, stop "npm start", pause OneDrive sync for this folder if needed.
REM 2) Double-click this file or run: clean-install.bat

cd /d "%~dp0"

echo Removing old lockfile...
if exist package-lock.json del /f /q package-lock.json

echo Removing node_modules (may take a minute)...
if exist node_modules (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "if (Test-Path 'node_modules') { Remove-Item -LiteralPath 'node_modules' -Recurse -Force -ErrorAction SilentlyContinue }"
)

echo Running npm install...
call npm install
if errorlevel 1 (
  echo.
  echo If this failed with EBUSY/EPERM/ENOTEMPTY: close all apps using this folder, pause OneDrive,
  echo reboot, then run this script again. Or move the project outside OneDrive.
  pause
  exit /b 1
)

echo Done.
pause
