#!/usr/bin/env python
# coding: utf-8

# JULY 2023
# Script that initializes the set of UMLS CSVs extracted from the Neptune data warehouse.
# 1. Reformats codes from SABs that do not comply with the standard format of SAB CODE.
#    Known cases are:
#    HGNC - from HGNC HGNC:CODE to HGNC:CODE
#    GO - from GO GO:CODE TO GO:CODE
#    HPO - from HPO HP:CODE TO HPO:CODE
#    HCPCS Level codes - from format like "HCPCS Level 3: E0181-E0199" to "HCPCS:Level_3_E0181-E0199".
# 2. Establishes the colon as the exclusive delimiter between SAB and CODE.

# The result is that every column in a UMLS CSV file that corresponds to a CodeID will be formatted as SAB:CODE.

# AUGUST 2023
# 3. For relationships (e.g., in CUI-CUIs.csv), replace dot and dash characters with underscores.
# 4. Replaces SUIs with terms.


# ------

import sys
import os
import numpy as np

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
# 2. Reformat relevant code colums:
#   a. Each of these files contains one or more columns that may contain codes from SABs that do not conform to the
#      standard format of SAB CODE. The known cases are:
#      HGNC and GO (which format as SAB SAB:CODE)
#      HPO (which formats as HPO HP:CODE)
#   b. Establish the colon as delimiter between SAB and CODE. This involves handling the special case of HCPCS Level codes.
# 3. Replace original file with converted file.

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

        # Delimiter:
        # If the code contains 'Level', remove the colon and replace all spaces with underscore;
        # otherwise, replace the space with a colon.
        dffile[col] = np.where(dffile[col].str.contains('Level'), dffile[col].str.replace(': ', '_').str.replace('Level ', 'Level_'), dffile[col])
        dffile[col] = dffile[col].str.replace(' ', ':')
    ulog.print_and_logger_info(f'Rewriting {csvfile}')
    print('DEBUG: not rewriting')
    # uextract.to_csv_with_progress_bar(df=dffile, path=csvfile, index=False)

# Obtain list of files with relationships that need reformatting.
dictrel_columns = config.get_section(section='Relationship_column')
for f in dictrel_columns:
    filename = f + '.csv'
    csvfile = csv_path(path=csvdir, file=filename)
    ulog.print_and_logger_info(f'Reading {csvfile}')
    dffile = uextract.read_csv_with_progress_bar(path=csvfile)

    # list of columns to reformat
    convert_columns = list(dictrel_columns[f].split(','))
    for col in convert_columns:
        ulog.print_and_logger_info(f'--Reformatting column {col}')
        dffile[col] = dffile[col].str.replace('.', '_', regex=False)
        dffile[col] = dffile[col].str.replace('-', '_', regex=False)
    ulog.print_and_logger_info(f'Rewriting {csvfile}')
    print('DEBUG: not rewriting')
    # uextract.to_csv_with_progress_bar(df=dffile, path=csvfile, index=False)

# REPLACE SUIs WITH TERMS.
# Logic:
# 1. Read:
#    SUIs.csv
#    CUI-SUIs.csv
#    CODE-SUIs.csv
# 2. Merge CUI-SUIs with SUIs and replace :END_ID in CUI-SUIs with name from SUIs
# 3. Merge CODE-SUIs with SUIs and replace :END_ID in CODE_SUIs with name from SUIs
# 4. Drop SUI:ID from SUIs

# Read files
fSUIs = 'SUIs.csv'
csvSUIs = csv_path(path=csvdir, file=fSUIs)
ulog.print_and_logger_info(f'Reading {csvSUIs}')
dfSUIs = uextract.read_csv_with_progress_bar(path=csvSUIs)

fCUISUIs = 'CUI-SUIs.csv'
csvCUISUIs = csv_path(path=csvdir, file=fCUISUIs)
ulog.print_and_logger_info(f'Reading {csvCUISUIs}')
dfCUISUIs = uextract.read_csv_with_progress_bar(path=csvCUISUIs)

fCODESUIs = 'CODE-SUIs.csv'
csvCODESUIs = csv_path(path=csvdir, file=fCODESUIs)
ulog.print_and_logger_info(f'Reading {csvCODESUIs}')
dfCODESUIs = uextract.read_csv_with_progress_bar(path=csvCODESUIs)

# Merge and replace.
dfCUISUIs = dfCUISUIs.merge(dfSUIs, how='inner', left_on=':END_ID', right_on=':SUI_ID')
dfCUISUIs = dfCUISUIs[['CUI', 'name']]
print('DEBUG: Not writing')
ulog.print_and_logger_info(f'Rewriting {csvCUISUIs}')
# uextract.to_csv_with_progress_bar(df=dfCUISUIs, path=csvCUISUIs, index=False)

dfCODESUIs = dfCODESUIs.merge(dfSUIs, how='inner', left_on=':END_ID', right_on=':SUI_ID')
dfCODESUIs = dfCUISUIs[['name', ':START_ID', ':TYPE', 'CUI']]
print('DEBUG: Not writing')
ulog.print_and_logger_info(f'Rewriting {csvCUISUIs}')
# uextract.to_csv_with_progress_bar(df=dfCUISUIs, path=csvCUISUIs, index=False)

dfSUIs = dfSUIs['name']
print('DEBUG: Not writing')
ulog.print_and_logger_info(f'Rewriting {csvSUIs}')
# uextract.to_csv_with_progress_bar(df=dfSUIs, path=csvSUIs, index=False)
