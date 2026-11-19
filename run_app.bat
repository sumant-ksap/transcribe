@echo off
rem Double-click to start the Hindi/Hinglish transcript app.
rem Add --share after app.py for a temporary public link.
cd /d "%~dp0"
".venv\Scripts\python.exe" app.py %*
pause
