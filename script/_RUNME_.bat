@echo off

cls

rem Sync files
python -u "%~dp0\backup.py"
pause
