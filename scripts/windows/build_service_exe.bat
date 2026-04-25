@echo off
setlocal
set "REPO_ROOT=%~dp0..\.."
pushd "%REPO_ROOT%"
for %%I in ("%CD%") do set "REPO_ROOT_ABS=%%~fI"
set "SERVICE_ENTRY=%REPO_ROOT_ABS%\scripts\windows\windows_service.py"
set "SERVICE_ICON=%REPO_ROOT_ABS%\installer\InsuranceManager.ico"

if not exist ".venv\Scripts\python.exe" (
  echo No .venv found. Run scripts\windows\recreate_venv.bat from the repo root first.
  exit /b 1
)
if not exist "%SERVICE_ENTRY%" (
  echo Missing "%SERVICE_ENTRY%".
  exit /b 1
)
if not exist "%SERVICE_ICON%" (
  echo Missing "%SERVICE_ICON%".
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

if exist "dist\InsuranceBackendService" rmdir /s /q "dist\InsuranceBackendService"
if exist "build\InsuranceBackendService" rmdir /s /q "build\InsuranceBackendService"

python -m PyInstaller ^
  --clean ^
  --onefile ^
  --name InsuranceBackendService ^
  --icon "%SERVICE_ICON%" ^
  --distpath "dist\InsuranceBackendService" ^
  --workpath "build\InsuranceBackendService" ^
  --specpath "build" ^
  --hidden-import win32timezone ^
  --collect-all fastapi ^
  --collect-all starlette ^
  --collect-all pydantic ^
  --collect-all dotenv ^
  --collect-all jwt ^
  --collect-all google ^
  --collect-all aiosqlite ^
  --collect-all requests ^
  --collect-all multipart ^
  --collect-submodules uvicorn ^
  --collect-submodules httptools ^
  --collect-submodules websockets ^
  "%SERVICE_ENTRY%"

if errorlevel 1 exit /b 1

if not exist "runtime" mkdir "runtime"
copy /Y "dist\InsuranceBackendService\InsuranceBackendService.exe" "runtime\InsuranceBackendService.exe" >nul
if errorlevel 1 exit /b 1

echo Built dist\InsuranceBackendService\InsuranceBackendService.exe
echo Copied runtime\InsuranceBackendService.exe
popd
