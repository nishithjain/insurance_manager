@echo off
setlocal
title Insurance Manager Cloudflare Tunnel

where cloudflared.exe >nul 2>&1
if errorlevel 1 (
  echo cloudflared.exe was not found on PATH.
  echo Install cloudflared, then open a new Command Prompt and try again.
  echo.
  pause
  exit /b 1
)

echo Starting Cloudflare Tunnel for Insurance Manager...
echo.
echo Local service:
echo   http://localhost:8000
echo.
echo Cloudflare will print a public https://...trycloudflare.com address below.
echo Keep this window open while you want the tunnel to stay running.
echo Press Ctrl+C to stop the tunnel.
echo.

cloudflared tunnel --url http://localhost:8000

echo.
echo Tunnel stopped.
pause
