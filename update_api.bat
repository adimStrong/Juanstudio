@echo off
echo ============================================================
echo   JuanStudio - Fetch Data from Facebook API
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/4] Fetching posts from Facebook API...
python fetch_missing_posts.py --no-notify

echo.
echo [2/4] Updating follower counts...
python update_followers.py

echo.
echo [3/4] Fetching comment data (self-comments)...
python fetch_comments.py

echo.
echo ============================================================
echo [4/4] Rebuilding static data for frontend...
echo ============================================================
python export_static_data.py

echo.
echo ============================================================
echo   Done! Data updated from API.
echo ============================================================
pause
