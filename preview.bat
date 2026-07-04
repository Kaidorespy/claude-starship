@echo off
echo.
echo   ========================================
echo      CLAUDE HUB - Quick Preview
echo      (UI only, demo mode)
echo   ========================================
echo.
cd /d "%~dp0\frontend"
start http://localhost:8080
python -m http.server 8080
pause
