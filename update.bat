@echo off
title JuanStudio Update
cd /d C:\Users\us\Desktop\juanstudio_project

echo ============================================================
echo JUANSTUDIO UPDATE
echo ============================================================
echo.
echo [1/3] Importing CSV files...
python csv_importer.py import-all "exports/from content manual Export"

echo.
echo [2/3] Exporting analytics...
python daily_update.py --export

echo.
echo [3/3] Sending Telegram notifications...
python daily_update.py --notify

echo.
echo ============================================================
echo UPDATE COMPLETE
echo.
echo Data updated locally. To push to Vercel, run: push.bat
echo ============================================================
pause
