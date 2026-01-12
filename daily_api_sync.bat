@echo off
cd /d C:\Users\us\Desktop\juanstudio_project

echo ============================================
echo JuanStudio API Sync - %date% %time%
echo ============================================
echo.

REM Step 1: Sync from Facebook API
echo [1/3] Fetching from Facebook API...
python fetch_missing_posts.py --no-notify

REM Step 2: Export static data
echo [2/3] Exporting analytics...
python export_static_data.py

REM Step 3: Git push if changes
echo [3/3] Checking for changes...
git diff --quiet frontend/public/data/analytics.json
if %errorlevel% neq 0 (
    echo Changes detected, pushing...
    git add frontend/public/data/analytics.json
    git commit -m "Daily API sync: %date%"
    git push origin main

    REM Notify on success
    powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('API data synced and deployed!', 'JuanStudio Daily Sync', 'OK', 'Information')"
) else (
    echo No changes detected.
)

echo ============================================
echo Done! %time%
echo ============================================
