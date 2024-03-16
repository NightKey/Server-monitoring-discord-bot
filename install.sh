#!bin/sh
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

python -m pip install virtualenv
x-terminal-emulator -e run.sh "$@"
