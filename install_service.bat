@echo off
setlocal
cd /d "%~dp0"

set "SERVICE_EXE=%~dp0InsuranceBackendService.exe"
if not exist "%SERVICE_EXE%" set "SERVICE_EXE=%~dp0runtime\InsuranceBackendService.exe"
if not exist "%SERVICE_EXE%" (
  echo Missing "%SERVICE_EXE%".
  echo Build the service executable before installing the service.
  exit /b 1
)

sc.exe query InsuranceBackendService >nul 2>&1
if not errorlevel 1 (
  echo InsuranceBackendService is already installed.
  sc.exe config InsuranceBackendService start= auto DisplayName= "Insurance Manager Backend Service"
  sc.exe description InsuranceBackendService "Runs the Insurance Manager FastAPI backend."
  exit /b 0
)

"%SERVICE_EXE%" --startup auto install
if errorlevel 1 exit /b 1

sc.exe config InsuranceBackendService start= auto DisplayName= "Insurance Manager Backend Service"
sc.exe description InsuranceBackendService "Runs the Insurance Manager FastAPI backend."
echo InsuranceBackendService installed.
