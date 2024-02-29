@ECHO off
SET main_dir=%~dp0
echo %main_dir%
cd %main_dir%

IF NOT EXIST venv\ (
    ECHO Creating new venv
    call virtualenv venv
    if NOT errorlevel 0 (
        call install.bat
        exit /b 0
    )
)

IF "%VIRTUAL_ENV%"=="" (
    ECHO Activating venv
    call venv/Scripts/activate.bat
)

start /wait python -m pip install --upgrade -r dependencies.txt
ECHO Starting bot
call python bot.py %*
ECHO Disabling venv
call venv/Scripts/deactivate.bat