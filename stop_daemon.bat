@echo off
echo Stopping JuanStudio Daemon...
taskkill /FI "WINDOWTITLE eq JuanStudio Daemon" 2>nul
echo Done.
pause
