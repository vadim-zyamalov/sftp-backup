@echo off

echo Process really fat files

SET PATH=%PATH%;"C:\Program Files\WinRAR\";"C:\Program Files (x86)\WinRAR\"

set curdir="%cd%"
cd /d "%~1"

call :treeProcess
cd /d "%curdir%"
goto :eof

:treeProcess
    rem Process really fat files
    for %%f in (*.dta,*.dat,*.tab,*.sas7bdat,*.sav) do (
        echo Processing fat file: %%~dpnxf
        if exist "%%f.rar" del "%%f.rar"
        rar a -rr -t -df -- "%%f.rar" "%%f"
    )

    for %%f in (*.csv,*.tsv,*.txt,*.raw,*.mdb) do (
        if %%~zf gtr 5000000 (
            echo Processing fat text file: %%~dpnxf
            if exist "%%f.rar" del "%%f.rar"
            rar a -rr -t -df -- "%%f.rar" "%%f"
        )
    )

    rem Converting archives to rar
    for %%f in (*.zip,*.gz,*.7z) do (
        echo Processing archive: %%~dpnxf
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
        echo Diving into: %%~dpnd
        cd %%~d
        call :treeProcess
        cd ..
    )
    exit /b
