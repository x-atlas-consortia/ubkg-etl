# UBKG Utilities

Functions that are common to scripts in the generation framework.

- ubkg_config.py: Functions related to configuration files
- ubkg_extract.py: Functions related to file i/o. In particular, functions in this script wrap various download and Pandas import/export functions with a TQDM progress bar.
- ubkg_logging.py: Functions related to logging
- ubkg_parsetools.py: Functions related to parsing and standardizing column data
- ubkg_subprocess.py: Functions related to calling subprocesses.

The file **parsetester.py** is a small application to test the codeReplacements function in ubkg_parsetools.py.