 #!/usr/bin/env bash
PATH_TO_DRIVER=$1
DRIVER_DIRECTORY="${PATH_TO_DRIVER%/*}/"
if test -f "$PATH_TO_DRIVER"
then
    echo "$PATH_TO_DRIVER exists."
else
    wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz
    tar -xvzf geckodriver*
    sudo mv geckodriver $DRIVER_DIRECTORY
fi
