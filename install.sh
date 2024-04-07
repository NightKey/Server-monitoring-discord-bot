#!bin/bash
cd "$(dirname "$0")"

python -m pip install virtualenv
x-terminal-emulator -e run.sh "$@"
