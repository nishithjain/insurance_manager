@echo off
setlocal
set "REPO_ROOT=%~dp0.."
pushd "%REPO_ROOT%"

if not exist "frontend\package.json" (
  echo Missing frontend\package.json.
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo npm was not found. Install Node.js on the build machine.
  exit /b 1
)

pushd frontend
if exist package-lock.json (
  call npm ci
) else (
  call npm install
)
if errorlevel 1 exit /b 1

call npm run build
if errorlevel 1 exit /b 1
popd

if not exist "frontend\build\index.html" (
  echo Expected React build output was not found at frontend\build.
  exit /b 1
)

if exist "installer_staging\frontend_dist" rmdir /s /q "installer_staging\frontend_dist"
mkdir "installer_staging\frontend_dist"
xcopy "frontend\build\*" "installer_staging\frontend_dist\" /E /I /Y
if errorlevel 1 exit /b 1

echo Built frontend and staged it at installer_staging\frontend_dist
popd
