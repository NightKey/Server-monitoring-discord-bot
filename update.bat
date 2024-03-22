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
    start /wait git pull
    echo "Update Installed!"
    exit /b 1
)

echo "Already up to date!"
exit /b 0