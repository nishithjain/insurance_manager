@echo off
setlocal
set "APP_DIR=%~dp0"
if not exist "%APP_DIR%config\backend_service_config.json" set "APP_DIR=%~dp0..\.."
pushd "%APP_DIR%"

set "SERVICE_EXE=%APP_DIR%\InsuranceBackendService.exe"
if not exist "%SERVICE_EXE%" set "SERVICE_EXE=%APP_DIR%\runtime\InsuranceBackendService.exe"

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
popd
