#!bin/sh
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

update.sh

if [ $? -eq 1 ]
then
    x-terminal-emulator -e run.sh "$@"
    exit 0
fi

#If venv doesn't exist, create venv and install dependencies.
if ! [ -d venv ]
then
    echo "venv doesn't exist, creating venv."
    python3 -m virtualenv venv
fi

if ! [ -d venv ]
then
    echo "Installing python virtualenv"
    x-terminal-emulator -e install.sh "$@"
    exit 0
fi

#If not in venv, activate venv.
if [[ "$VIRTUAL_ENV" == "" ]]
then
    source venv/bin/activate
fi

pip install -r dependencies.txt --upgrade
echo "Starting bot"
python bot.py
deactivate
