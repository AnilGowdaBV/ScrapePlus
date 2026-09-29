@echo off
title ScrapePlus - Login to LinkedIn
cd /d "%~dp0"
echo ============================================================
echo   Opening Chrome for LinkedIn Login
echo ============================================================
echo.
echo Please log in with your ID and password in the Chrome window.
echo Once logged in, your session is saved automatically!
echo.
call .\.venv\Scripts\python.exe scripts\open_browser.py
pause
