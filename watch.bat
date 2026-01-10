@echo off
title JuanStudio New Post Watcher
cd /d C:\Users\us\Desktop\juanstudio_project

echo ============================================================
echo JUANSTUDIO NEW POST WATCHER
echo ============================================================
echo.
echo Checking every hour for new posts...
echo Press Ctrl+C to stop
echo.

python new_post_watcher.py --daemon

pause
