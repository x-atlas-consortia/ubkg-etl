#!/bin/bash

# A POSIX variable
OPTIND=1         # Reset in case getopts has been used previously in the shell.

VENV=./venv
which python3
status=$?
if [[ $status != 0 ]] ; then
    echo '*** Python3 must be installed!'
    exit
fi

if [[ -d ${VENV} ]] ; then
    echo "*** Using python3 venv in ${VENV}"
    source ${VENV}/bin/activate
else
    echo "*** Installing python3 venv to ${VENV}"
    python3 -m venv ${VENV}
    python3 -m pip install --upgrade pip
    source ${VENV}/bin/activate
    pip install -r requirements.txt
    brew install wget
    echo "*** Done installing python3 venv"
fi

./build_csv.py "$@"
