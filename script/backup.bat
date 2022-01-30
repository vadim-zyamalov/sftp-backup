@echo off

echo Process really fat files

SET PATH=%PATH%;"C:\Program Files\WinRAR\";"C:\Program Files (x86)\WinRAR\"

set curdir="%cd%"
cd "%~1"

call :treeProcess
cd "%curdir%"
goto :eof

:treeProcess
    rem Process really fat files
    for %%f in (*.dta,*.dat,*.csv,*.tab,*.sas7bdat,*.sav,*.raw) do (
        @echo "%%~dpnxf"
        if exist "%%f.rar" del "%%f.rar"
        rar a -rr -t -df -- "%%f.rar" "%%f"
    )
        
    rem Converting archives to rar
    for %%f in (*.zip,*.gz,*.7z) do (
        @echo "%%~dpnxf"
        if exist "%%~nf.rar" del "%%~nf.rar"
        winrar x -inul -- "%%f" * "%%~df\_tmp\"
        if NOT ERRORLEVEL 1 (
            cd "%%~df\_tmp\"
            rar a -r -rr -t -df -- "%%~dpf\%%~nf.rar" *
            cd "%%~dpf"
            del "%%f"
        )
        rmdir /S /Q "%%~df\_tmp\"
    )
    
    rem Dive into subfolders
    for /D %%d in (*) do (
        cd "%%~d"
        echo %%~dpd
        call :treeProcess
        cd ..
    )
    exit /b

