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

echo Installing Zotify...
%PYTHON% -m pip install --upgrade git+https://github.com/Googolplexed0/zotify.git
if errorlevel 1 (
    echo Zotify installation failed.
    pause
    exit /b 1
)

echo Creating or updating Zotify configuration...
%PYTHON% -m zotify --update-config
if errorlevel 1 (
    echo Zotify could not create or update its configuration.
    pause
    exit /b 1
)

%PYTHON% "%~dp0setup.py"
if errorlevel 1 (
    echo Spotify setup did not complete.
    pause
    exit /b 1
)

echo.
echo Spotify setup is complete.
pause
