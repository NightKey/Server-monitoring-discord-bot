@ECHO off
SET main_dir=%~dp0
echo %main_dir%
cd %main_dir%

start /wait update.bat

if ERRORLEVEL 1 (
    call rub.bat %*
    exit /b 0
)

IF NOT EXIST venv\ (
    ECHO Venv doesn't exist, creating venv.
    call python -m virtualenv venv
)

IF NOT EXIST venv\ (
    ECHO Installing python virtualenv
    start install.bat %*
    exit /b 0
)

IF "%VIRTUAL_ENV%"=="" (
    call venv/Scripts/activate.bat
)

start /wait python -m pip install --upgrade -r dependencies.txt
ECHO Starting bot
call python bot.py %*
call venv/Scripts/deactivate.bat
