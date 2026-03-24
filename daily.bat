@echo off
title JuanStudio - Daily Update
cd /d C:\Users\us\Desktop\juanstudio_project

set GIT="C:\Users\us\AppData\Local\Programs\Git\bin\git.exe"
set ERRORS=0

echo ============================================================
echo   JUANSTUDIO DAILY UPDATE
echo   %date% %time%
echo ============================================================
echo.

echo [1/6] Fetching new posts from API...
python fetch_missing_posts.py --silent
if errorlevel 1 (
    echo ERROR: fetch_missing_posts.py failed!
    set /a ERRORS+=1
)

echo.
echo [2/6] Importing CSV views/reach...
if exist "exports\from content manual Export\*.csv" (
    python import_manual_exports.py
    if errorlevel 1 (
        echo ERROR: import_manual_exports.py failed!
        set /a ERRORS+=1
    )
) else (
    echo   No CSV files found - skipping. Views/reach won't update.
)

echo.
echo [3/6] Backfilling views/reach from API insights...
python backfill_views_reach.py
if errorlevel 1 (
    echo ERROR: backfill_views_reach.py failed!
    set /a ERRORS+=1
)

echo.
echo [4/6] Cleaning up duplicates...
python cleanup_duplicates.py
if errorlevel 1 (
    echo ERROR: cleanup_duplicates.py failed!
    set /a ERRORS+=1
)

echo.
echo [5/6] Exporting static data...
python export_static_data.py
if errorlevel 1 (
    echo ERROR: export_static_data.py failed!
    set /a ERRORS+=1
    echo STOPPING - export failed, will not deploy bad data.
    pause
    exit /b 1
)

echo.
echo [6/6] Deploying to Vercel...
%GIT% add -A
%GIT% commit -m "Daily update - %date% %time%"
%GIT% push origin main
call npx vercel --prod --yes --force

echo.
echo ============================================================
if %ERRORS% GTR 0 (
    echo   DONE WITH %ERRORS% WARNING(S) - check output above
) else (
    echo   DONE - ALL STEPS SUCCESSFUL
)
echo   Live: https://juanstudio-analytics.vercel.app
echo ============================================================
pause
