@echo off
setlocal
sc.exe query InsuranceBackendService >nul 2>&1
if errorlevel 1 (
  echo InsuranceBackendService is not installed.
  exit /b 0
)

sc.exe query InsuranceBackendService | findstr /I "RUNNING" >nul 2>&1
if errorlevel 1 (
  echo InsuranceBackendService is not running.
  exit /b 0
)

net.exe stop InsuranceBackendService
