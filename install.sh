#!bin/bash

echo $'\033]30;Server Monitoring Discord Bot\007'

cd "$(dirname "$0")"

python -m pip install virtualenv
x-terminal-emulator -e run.sh "$@"
