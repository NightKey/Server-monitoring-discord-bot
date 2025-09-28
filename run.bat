@ECHO off
SET main_dir=%~dp0
cd %main_dir%

TITLE Server Monitoring Discord Bot

call update.bat

if ERRORLEVEL 1 (
    start run.bat %*
    exit /b 0
)

IF NOT EXIST venv\ (
    ECHO Venv doesn't exist, creating venv.
    call python -m venv venv
)

IF NOT EXIST venv\ (
    ECHO Installing python venv
    start install.bat %*
    exit /b 0
)

IF "%VIRTUAL_ENV%"=="" (
    call venv/Scripts/activate.bat
)

call python -m pip install -r dependencies.txt --upgrade
ECHO Starting bot
call python bot.py %*
call venv/Scripts/deactivate.bat
