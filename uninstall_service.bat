@echo off
setlocal
cd /d "%~dp0"

set "SERVICE_EXE=%~dp0InsuranceBackendService.exe"
if not exist "%SERVICE_EXE%" set "SERVICE_EXE=%~dp0runtime\InsuranceBackendService.exe"

sc.exe query InsuranceBackendService >nul 2>&1
if errorlevel 1 (
  echo InsuranceBackendService is not installed.
  exit /b 0
)

net.exe stop InsuranceBackendService >nul 2>&1
if exist "%SERVICE_EXE%" (
  "%SERVICE_EXE%" remove
) else (
  sc.exe delete InsuranceBackendService
)
echo InsuranceBackendService uninstalled.
