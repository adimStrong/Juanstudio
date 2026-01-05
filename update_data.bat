@echo off
title JuanStudio - Update Data
color 0A
cd /d C:\Users\us\Desktop\juanstudio_project

:MENU
echo.
echo ============================================================
echo JuanStudio Data Update Tool
echo ============================================================
echo.
echo   [1] CSV Import (Meta exports) + Export + Push
echo   [2] API Fetch (posts + comments) + Export + Push
echo   [3] Verify Data Only (check for issues)
echo   [4] Exit
echo.
set /p choice="Enter choice (1-4): "

if "%choice%"=="1" goto CSV_UPDATE
if "%choice%"=="2" goto API_UPDATE
if "%choice%"=="3" goto VERIFY_ONLY
if "%choice%"=="4" goto END
echo Invalid choice. Try again.
goto MENU

:CSV_UPDATE
echo.
echo ============================================================
echo [1/3] CSV IMPORT - Importing from manual exports...
echo ============================================================
dir /b "exports\from content manual Export\*.csv" 2>nul
echo.
python import_manual_exports.py
if errorlevel 1 (
    echo ERROR: CSV import failed
    pause
    goto MENU
)

echo.
echo ============================================================
echo [2/3] EXPORT - Generating JSON for frontend...
echo ============================================================
python export_static_data.py

echo.
echo ============================================================
echo [3/3] PUSH - Committing and pushing to GitHub...
echo ============================================================
set GIT="C:\Users\us\AppData\Local\Programs\Git\bin\git.exe"
%GIT% add -A
%GIT% commit -m "CSV update - %date%"
%GIT% push origin main

echo.
echo ============================================================
echo DONE! CSV update complete.
echo ============================================================
pause
goto MENU

:API_UPDATE
echo.
echo ============================================================
echo [1/5] API FETCH - Fetching missing posts...
echo ============================================================
python fetch_missing_posts.py

echo.
echo ============================================================
echo [2/5] API FETCH - Fetching comments (10 workers)...
echo ============================================================
python fetch_comments.py --workers 10

echo.
echo ============================================================
echo [3/5] API FETCH - Updating follower counts...
echo ============================================================
python update_fan_counts.py

echo.
echo ============================================================
echo [4/5] EXPORT - Generating JSON for frontend...
echo ============================================================
python export_static_data.py

echo.
echo ============================================================
echo [5/5] PUSH - Committing and pushing to GitHub...
echo ============================================================
set GIT="C:\Users\us\AppData\Local\Programs\Git\bin\git.exe"
%GIT% add -A
%GIT% commit -m "API update - %date%"
%GIT% push origin main

echo.
echo ============================================================
echo DONE! API update complete.
echo ============================================================
pause
goto MENU

:VERIFY_ONLY
echo.
echo ============================================================
echo DATA VERIFICATION
echo ============================================================
python smart_verify.py --check-only
echo.
pause
goto MENU

:END
echo Goodbye!
exit /b
