#!/bin/bash

# set PYTHONPATH to OpenTURNS if needed
PYOT=$(echo $HOME/ot/trunk/build/install/lib/python2.7/site-packages)
PYOT=$(echo $PWD/../../../build/install/lib/python2.7/site-packages):$PYOT
export PYTHONPATH=$PYOT:$PYTHONPATH

# start the script
python ot_script.py
