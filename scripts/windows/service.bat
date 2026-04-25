@echo off
setlocal

:: Check for Administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as an Administrator.
    exit /b 1
)

set "SERVICE_NAME=InsuranceBackendService"
set "DISPLAY_NAME=Insurance Manager Backend Service"
set "DESCRIPTION=Runs the Insurance Manager FastAPI backend."

set "APP_DIR=%~dp0"
if not exist "%APP_DIR%config\backend_service_config.json" set "APP_DIR=%~dp0..\.."

pushd "%APP_DIR%" >nul

:: Resolve Service Executable path once for use in install/uninstall
set "SERVICE_EXE=%APP_DIR%\InsuranceBackendService.exe"
if not exist "%SERVICE_EXE%" set "SERVICE_EXE=%APP_DIR%\runtime\InsuranceBackendService.exe"
if not exist "%SERVICE_EXE%" set "SERVICE_EXE=%APP_DIR%\dist\InsuranceBackendService\InsuranceBackendService.exe"

if "%~1"=="" goto :usage

set "ACTION=%~1"

if /I "%ACTION%"=="install" goto :install
if /I "%ACTION%"=="status" goto :status
if /I "%ACTION%"=="start" goto :start
if /I "%ACTION%"=="stop" goto :stop
if /I "%ACTION%"=="restart" goto :restart
if /I "%ACTION%"=="uninstall" goto :uninstall
if /I "%ACTION%"=="remove" goto :uninstall

goto :usage

:install
if not exist "%SERVICE_EXE%" (
    echo Missing InsuranceBackendService.exe.
    echo Checked:
    echo   "%APP_DIR%\InsuranceBackendService.exe"
    echo   "%APP_DIR%\runtime\InsuranceBackendService.exe"
    echo   "%APP_DIR%\dist\InsuranceBackendService\InsuranceBackendService.exe"
    echo Build the service executable before installing the service.
    goto :exit_err
)

sc.exe query "%SERVICE_NAME%" >nul 2>&1
if not errorlevel 1 (
    echo %SERVICE_NAME% is already installed.
    sc.exe config "%SERVICE_NAME%" start= auto DisplayName= "%DISPLAY_NAME%"
    sc.exe description "%SERVICE_NAME%" "%DESCRIPTION%"
    goto :exit_ok
)

"%SERVICE_EXE%" --startup auto install
if errorlevel 1 (
    goto :exit_err
)

sc.exe query "%SERVICE_NAME%" >nul 2>&1
if errorlevel 1 (
    echo Failed to install %SERVICE_NAME%.
    echo Run this command from an elevated Administrator terminal.
    goto :exit_err
)

sc.exe config "%SERVICE_NAME%" start= auto DisplayName= "%DISPLAY_NAME%"
sc.exe description "%SERVICE_NAME%" "%DESCRIPTION%"

echo %SERVICE_NAME% installed.
goto :exit_ok


:status
sc.exe query "%SERVICE_NAME%" >nul 2>&1
if errorlevel 1 (
    echo %SERVICE_NAME% is NOT installed.
    goto :exit_err
)

for /f "tokens=3 delims=: " %%H in ('sc query "%SERVICE_NAME%" ^| findstr /I "STATE"') do (
    set "STATE=%%H"
)

echo %SERVICE_NAME% status: %STATE%
goto :exit_ok


:start
sc.exe query "%SERVICE_NAME%" >nul 2>&1
if errorlevel 1 (
    echo %SERVICE_NAME% is NOT installed.
    goto :exit_err
)

sc.exe query "%SERVICE_NAME%" | findstr /I "RUNNING" >nul
if not errorlevel 1 (
    echo %SERVICE_NAME% is already running.
    goto :exit_ok
)

net.exe start "%SERVICE_NAME%"
goto :exit_ok


:stop
sc.exe query "%SERVICE_NAME%" >nul 2>&1
if errorlevel 1 (
    echo %SERVICE_NAME% is NOT installed.
    goto :exit_err
)

sc.exe query "%SERVICE_NAME%" | findstr /I "STOPPED" >nul
if not errorlevel 1 (
    echo %SERVICE_NAME% is already stopped.
    goto :exit_ok
)

net.exe stop "%SERVICE_NAME%"
goto :exit_ok


:restart
sc.exe query "%SERVICE_NAME%" >nul 2>&1
if errorlevel 1 (
    echo %SERVICE_NAME% is NOT installed.
    goto :exit_err
)
net.exe stop "%SERVICE_NAME%" >nul 2>&1
timeout /t 3 >nul
net.exe start "%SERVICE_NAME%"
goto :exit_ok


:uninstall
sc.exe query "%SERVICE_NAME%" >nul 2>&1
if errorlevel 1 (
    echo %SERVICE_NAME% is NOT installed.
    goto :exit_ok
)

net.exe stop "%SERVICE_NAME%" >nul 2>&1

if exist "%SERVICE_EXE%" (
    "%SERVICE_EXE%" remove
) else (
    sc.exe delete "%SERVICE_NAME%"
)

if errorlevel 1 (
    echo Failed to delete %SERVICE_NAME%.
    goto :exit_err
)

echo %SERVICE_NAME% removed.
goto :exit_ok

popd
exit /b 0


:usage
echo.
echo Usage:
echo   service.bat install   - Install InsuranceBackendService
echo   service.bat status    - Check service status
echo   service.bat start     - Start service
echo   service.bat stop      - Stop service
echo   service.bat restart   - Restart service
echo   service.bat uninstall - Remove the Windows service
echo.
:exit_err
popd
exit /b 1

:exit_ok
popd
exit /b 0
