#!/usr/bin/env python
# coding: utf-8
import shlex
import subprocess
import sys

# Functions related to working with subprocesses.

def call_subprocess(command_line_str: str) -> None:

    # Format arguments list.
    # The assumption is that the argument was originally built for a call to sys.os.

    runargs = shlex.split(command_line_str)
    try:
        result = subprocess.run(runargs, check=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f'ERROR from subprocess {runargs} with return code {e.returncode}.')
        if not e.stderr is None:
            print(e.stderr)
        sys.exit(1)

    return
