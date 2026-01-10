@echo off
title JuanStudio Daemon
cd /d C:\Users\us\Desktop\juanstudio_project

echo ============================================================
echo JUANSTUDIO DAEMON
echo ============================================================
echo.
echo Schedule:
echo   - Every hour: Fetch API + notify new posts
echo   - At 6:00 AM: Export + push to Vercel
echo.
echo Press Ctrl+C to stop
echo ============================================================
echo.

python juanstudio_daemon.py

pause
