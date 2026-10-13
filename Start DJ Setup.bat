@echo off
setlocal

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0app\launcher.py"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3 was not found. Install Python 3.10 or newer and try again.
        pause
        exit /b 1
    )
    python "%~dp0app\launcher.py"
)
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" pause
exit /b %RESULT%
