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
        result = subprocess.run(runargs, capture_output=True, text=True)
    except:
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    return