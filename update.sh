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
    echo "Updates installed!"
    exit 1
fi

echo "Already up to date"
exit 0