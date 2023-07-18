#!/usr/bin/env python
# coding: utf-8

# JULY 2023
# Script that initializes the set of UMLS CSVs extracted from the Neptune data warehouse.
# Reformats codes from SABs that do not comply with the standard format of SAB CODE.
# Known cases are:
# HGNC (which formats as HGNC HGNC:CODE)
# GO (which formats as GO GO:CODE)
# HPO (which formats as HPO HP:CODE)
# ------

import sys
import os
import pandas as pd

# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path. (This assumes that this script is being called from build_csv.py.)
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)

# Logging module
import ubkg_logging as ulog
# Extracting files
import ubkg_extract as uextract
# Config file
import ubkg_config as uconfig


def csv_path(path: str, file: str) -> str:
    # Appends the CSV path to the file argument.
    return os.path.join(path, file)


# ------------------

# START
# Read from config file.
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/umls_init/umls_init.ini')
config = uconfig.ubkgConfigParser(path=cfgfile, case_sensitive=True)

# Obtain the CSV directory path.
csvdir = config.get_value(section='Directory', key='csvdir')

# Obtain list of files and columns to convert.
dictfile_columns = config.get_section(section='File_column')

# Obtain list of SABs that do not conform to SAB CODE formatting.
dictsabs = config.get_section(section='Duplicate_SAB')

# 1. Read each file that should be converted.
#   Each of these files contains one or more columns that may contain codes from SABs that do not conform to the
#   standard format of SAB CODE. The known cases are:
#   HGNC and GO (which format as SAB SAB:CODE)
#   HPO (which formats as HPO HP:CODE)

# 2. Replace original file with converted file.

for f in dictfile_columns:
    filename = f + '.csv'
    csvfile = csv_path(path=csvdir, file=filename)
    ulog.print_and_logger_info(f'Reading {csvfile}')
    dffile = uextract.read_csv_with_progress_bar(path=csvfile)

    # list of columns to reformat
    convert_columns = list(dictfile_columns[f].split(','))

    for col in convert_columns:
        ulog.print_and_logger_info(f'--Reformatting column {col}')

        for sabkey in dictsabs:
            sabstring = dictsabs[sabkey]
            dffile[col] = dffile[col].str.replace(sabstring, '')

    ulog.print_and_logger_info(f'Rewriting {csvfile}')
    uextract.to_csv_with_progress_bar(df=dffile, path=csvfile, index=False)