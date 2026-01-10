@echo off
title JuanStudio - Import Data from CSV Files
cd /d C:\Users\us\Desktop\juanstudio_project

echo ============================================================
echo   JuanStudio - Import Data from CSV Files
echo ============================================================
echo.
echo Place your CSV files in: exports\from content manual Export\
echo.

if not exist "exports\from content manual Export" (
    mkdir "exports\from content manual Export"
    echo Created folder. Add your CSV files there.
    pause
    exit /b
)

echo Importing CSV data...
python import_manual_exports.py

echo.
echo ============================================================
echo   Rebuilding static data for frontend...
echo ============================================================
python export_static_data.py

echo.
echo ============================================================
echo   Done! Data imported from CSV.
echo ============================================================
pause
