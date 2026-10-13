@echo off
setlocal

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3 was not found. Install Python 3 and run setup.bat first.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

if "%~1"=="" (
    %PYTHON% "%~dp0download.py" "%~dp0download-links.txt"
) else (
    %PYTHON% "%~dp0download.py" "%~1"
)
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" echo One or more downloads failed. Review the output and retry.
pause
exit /b %RESULT%
