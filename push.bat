@echo off
title JuanStudio Push to Vercel
cd /d C:\Users\us\Desktop\juanstudio_project

set GIT="C:\Users\us\AppData\Local\Programs\Git\bin\git.exe"

echo ============================================================
echo PUSH TO VERCEL (JuanStudio)
echo ============================================================
echo.

echo [1/3] Adding changes...
%GIT% add -A

echo.
echo [2/3] Committing changes...
%GIT% commit -m "Update data - %date% %time%"

echo.
echo Pushing to GitHub...
%GIT% push origin main

echo.
echo ============================================================
echo [3/3] Deploying frontend to Vercel...
echo ============================================================
cd frontend
call npx vercel --prod --yes

echo.
echo ============================================================
echo DEPLOY COMPLETE
echo Live: https://juanstudio-analytics.vercel.app
echo ============================================================
pause
