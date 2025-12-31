@echo off
color 0A
title JUANBABES - REPORT UPDATE
cd /d C:\Users\us\Desktop\juanbabes_project

echo.
echo ============================================
echo JuanBabes Report Update - %date% %time%
echo ============================================
echo.

REM Step 1: Import all CSVs from manual export folder
echo [1/4] Importing CSV data...
python csv_importer.py import-all "exports\from content manual Export" --mode merge
if %errorlevel% neq 0 (
    echo ERROR: CSV import failed!
    pause
    exit /b 1
)

REM Step 2: Export static data for frontend
echo.
echo [2/4] Exporting analytics data...
python export_static_data.py
if %errorlevel% neq 0 (
    echo ERROR: Export failed!
    pause
    exit /b 1
)

REM Step 3: Git commit and push
echo.
echo [3/4] Pushing to GitHub...
git add -A
git commit -m "Report update: %date% - CSV import and analytics refresh"
git push origin main
if %errorlevel% neq 0 (
    echo WARNING: Git push may have failed. Retrying...
    git push origin main
)

REM Step 4: Notify user
echo.
echo [4/4] Complete!
echo.
echo ============================================
echo DONE! Report updated and pushed to Railway.
echo ============================================
echo.
echo Railway will auto-deploy in 1-2 minutes.
echo Check: https://juanababes-production.up.railway.app/
echo.

powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Report updated and pushed to Railway!', 'JuanBabes Update Complete', 'OK', 'Information')" >nul 2>&1

pause
