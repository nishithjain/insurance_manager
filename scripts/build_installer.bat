@echo off
setlocal
set "REPO_ROOT=%~dp0.."
pushd "%REPO_ROOT%"

call "%~dp0build_service_exe.bat"
if errorlevel 1 exit /b 1

call "%~dp0build_frontend.bat"
if errorlevel 1 exit /b 1

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  where ISCC.exe >nul 2>&1
  if errorlevel 1 (
    echo Inno Setup Compiler was not found.
    echo Install Inno Setup 6 or add ISCC.exe to PATH.
    exit /b 1
  )
  set "ISCC=ISCC.exe"
)

"%ISCC%" "installer\InsuranceManagerBackend.iss"
if errorlevel 1 exit /b 1
echo Built installer_output\InsuranceManagerBackendSetup.exe
popd
