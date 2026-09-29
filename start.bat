@echo off
title ScrapePlus - LinkedIn People Search Platform
echo ============================================================
echo   Starting ScrapePlus (Local Mode)
echo ============================================================
echo.

cd /d "%~dp0"

if not exist .env (
    echo [*] Creating .env file from .env.example...
    copy .env.example .env >nul
)

echo [*] Checking database migrations...
call .\.venv\Scripts\python.exe -m alembic upgrade head

echo.
echo [*] Starting FastAPI Backend on port 8000...
start /b "" .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

timeout /t 2 /nobreak >nul

echo [*] Starting Frontend on port 5173...
cd frontend
start /b "" cmd.exe /c "npm run dev -- --host 127.0.0.1"

timeout /t 3 /nobreak >nul

echo.
echo ============================================================
echo   ScrapePlus is now LIVE!
echo   Opening: http://localhost:5173
echo ============================================================
echo.

start http://localhost:5173

echo Press Ctrl+C or close this window to stop both servers.
pause >nul
