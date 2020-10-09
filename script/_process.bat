@echo off

cls

rem Sync files
python "%~dp0\backup.py"
pause
