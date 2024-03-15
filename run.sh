#!bin/sh
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

git remote update
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

echo "Current: $LOCAL"
echo "Remote: $REMOTE"

if [ "$LOCAL" != "$REMOTE" ]
then
    git pull
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

pip install --upgrade -r dependencies.txt
echo "Starting bot"
python bot.py
deactivate