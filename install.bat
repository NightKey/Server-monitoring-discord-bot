@echo off
SET main_dir=%~dp0
echo %main_dir%
cd %main_dir%

start /wait python -m pip install venv
call run.bat %*
