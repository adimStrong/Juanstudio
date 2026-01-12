@echo off
color 0A
title JUANSTUDIO - DAILY API SYNC SCHEDULER
cls

echo.
echo ============================================================
echo JUANSTUDIO - DAILY API SYNC SCHEDULER
echo ============================================================
echo.
echo This will run the API sync automatically at 6:00 AM daily:
echo.
echo  Step 1: Fetch data from Facebook API
echo  Step 2: Export analytics to JSON
echo  Step 3: Push to GitHub (Vercel auto-deploys)
echo  Step 4: Show notification when complete
echo.
echo ============================================================
echo  Leave this window open! It will run at 6 AM.
echo  Press Ctrl+C to stop the scheduler
echo ============================================================
echo.

cd /d "C:\Users\us\Desktop\juanstudio_project"
python auto_sync_daemon.py

pause
