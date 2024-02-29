@ECHO off
SET main_dir=%~dp0
echo %main_dir%
cd %main_dir%

call git remote update

for /f %%i in ('git rev-parse @') do SET current=%%i
for /f %%i in ('git rev-parse @{u}') do SET remote=%%i

ECHO Current: %current%
ECHO Remote: %remote%

if NOT %current%==%remote% (
    ECHO Updating from remote
    start /wait git pull
    start run.bat
    exit /b 0
)

IF NOT EXIST venv\ (
    ECHO Creating new venv
    call virtualenv venv
)

IF NOT EXIST venv\ (
    ECHO venv couldn't be prepared!
    start install.bat
    exit /b 0
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