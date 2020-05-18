@echo off

cls

rem Sync files
echo "%~dp0\backup_step1.py"
python "%~dp0\backup_step1.py" -s %1 -t %2

pause
cls

rem Deal with archives
"%~dp0\backup_step2.bat" %2

pause
