#!/bin/bash

# Python version dependency:
# The PheKnowLator package uses the ray package.
# As of March 2023, ray does not support 3.11 of Python.
# This script assumes that Python 3.10 is installed via pyenv.
# If the global version of Python is prior to 3.11, it is not necessary to set the version, and
# you can comment out both the following line and the final line.

# Temporarily set Python version to 3.10.4
export PYENV_VERSION=3.10.4
echo "Python version:"
python --version

# A POSIX variable
OPTIND=1         # Reset in case getopts has been used previously in the shell.
VENV=./venv

# Check for install of Python
which python3
status=$?
if [[ $status != 0 ]] ; then
    echo '*** Python3 must be installed!'
    exit
fi

if [[ -d ${VENV} ]] ; then
    echo "*** Using Python venv in ${VENV}"
    source ${VENV}/bin/activate
else
    echo "*** Installing Python venv to ${VENV}"
    python -m venv ${VENV}
    python -m pip install --upgrade pip
    source ${VENV}/bin/activate
    echo "*** Installing required packages..."
    pip install -r requirements.txt
    brew install wget
    echo "*** Done installing python venv"
fi

echo "Running build_csv.py in venv..."
./build_csv.py "$@"

# Reset version to default
unset PYENV_VERSION
