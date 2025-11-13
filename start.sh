#!/usr/bin/bash

if [ ! -d .venv ]; then
        python3 -m venv .venv
fi
if [ -f .venv/bin/activate ]; then
        source .venv/bin/activate
else
        echo "No valid venv-Enivironment available"
        exit 1
fi
pip install -r requirements.txt

export DISPLAY=:0.0
python3 chromiumseturl.py $1
