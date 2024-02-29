@echo off
SET main_dir=%~dp0
echo %main_dir%
cd %main_dir%

ECHO Installing virtualenv
start /wait python -m pip install virtualenv
call run.bat