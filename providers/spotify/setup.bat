@echo off
setlocal

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3 was not found. Install Python 3.10 or newer and try again.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

%PYTHON% "%~dp0install.py" %*
if errorlevel 1 (
    echo Spotify setup did not complete.
    pause
    exit /b 1
)

echo.
echo Spotify setup is complete.
pause
