@echo off

cls

for /f "tokens=1,2 delims=;" %%i in (%~dp0\process_list.txt) do (
	rem Sync files
	echo "%~dp0\backup_step1.py"
	python "%~dp0\backup_step1.py" -s "%%~i" -t "%%~j"

	cls

	rem Deal with archives
	"%~dp0\backup_step2.bat" "%%~j"
)

pause
