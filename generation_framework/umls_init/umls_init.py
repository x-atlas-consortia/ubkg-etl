#!/usr/bin/env python
# coding: utf-8

# FEBRUARY 2024
# Replace HPO with HP in CUI-CUIs.csv

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
# 5. Add columns with blank values:
#    a. CODES.csv -value:float,lowerbound:float,upperbound:float,unit
#    b. CUI-CUIs.csv - evidence_class:string


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

import ubkg_parsetools as uparse


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

#--- ADDING columns
fcsv = csv_path(path=csvdir, file='CODEs.csv')
# value, lowerbound, and upperbound should be numbers.
# AUG 2025 - submitter values
new_header_columns = ['CodeID:ID', 'SAB', 'CODE', 'value:float', 'lowerbound:float', 'upperbound:float', 'unit',
                      'firstname','lastname','email']
uextract.update_columns_to_csv_header(fcsv, new_header_columns, fill=True)

fcsv = csv_path(path=csvdir, file='CUI-CUIs.csv')
# evidence_class should be a string.
new_header_columns = [':START_ID', ':END_ID', ':TYPE,SAB', 'evidence_class:string']
uextract.update_columns_to_csv_header(fcsv, new_header_columns, fill=True)

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

    # JAS JANUARY 2024
    # Rename the HPO SAB to HP.
    if f == 'CODEs':
        dffile['SAB'] = np.where(dffile['SAB']=='HPO', 'HP', dffile['SAB'])

    # list of columns to reformat
    convert_columns = list(dictfile_columns[f].split(','))

    for col in convert_columns:
        ulog.print_and_logger_info(f'--Reformatting column {col}')

        # JAS JANUARY 2024
        # Handle special case of HPO nodes.
        # The UMLS format for HPO nodes is HPO HP:<code>.
        # The format used by all other ontologies is HP:<code>.
        dffile[col] = np.where(dffile[col].str.contains('HPO HP:'),
                               dffile[col].str.replace('HPO HP:', 'HP:'), dffile[col])

        for sabkey in dictsabs:
            sabstring = dictsabs[sabkey]
            dffile[col] = dffile[col].str.replace(sabstring, '')

        # Delimiter:
        # If the code contains 'Level', remove the colon and replace all spaces with underscore;
        # otherwise, replace the space with a colon.
        dffile[col] = np.where(dffile[col].str.contains('Level'), dffile[col].str.replace(': ', '_').str.replace('Level ', 'Level_'), dffile[col])

        dffile[col] = dffile[col].str.replace(' ', ':')

    ulog.print_and_logger_info(f'Rewriting {csvfile}')
    uextract.to_csv_with_progress_bar(df=dffile, path=csvfile, index=False)

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
        # JANUARY 2024
        # dffile[col] = dffile[col].str.replace('.', '_', regex=False)
        # dffile[col] = dffile[col].str.replace('-', '_', regex=False)

        dffile[col] = uparse.relationReplacements(dffile[col])

    # February 2024
    # Convert SAB HPO to HP.
    ulog.print_and_logger_info(f'--Converting HPO to HP in SAB column')
    dffile['SAB'] = dffile['SAB'].str.replace('HPO', 'HP', regex=False)

    ulog.print_and_logger_info(f'Rewriting {csvfile}')
    uextract.to_csv_with_progress_bar(df=dffile, path=csvfile, index=False)

# REPLACE SUIs WITH TERMS.
# Logic:
# 1. Read:
#    SUIs.csv
#    CUI-SUIs.csv
#    CODE-SUIs.csv
# 2. Merge CUI-SUIs with SUIs and replace :END_ID in CUI-SUIs with name from SUIs
# 3. Merge CODE-SUIs with SUIs and replace :END_ID in CODE_SUIs with name from SUIs
# 4. Drop SUI:ID from SUIs

ulog.print_and_logger_info('Replacing SUI with name....')
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

# ISSUE - Codes in UMLS can have term types of "name alias". The term type abbreviation of NA is reserved
# in Pandas/Numpy; Pandas converts the string of 'NA' in :TYPE to np.na, which results in import failure later.
# Change the term type to NAME_ALIAS.
dfCODESUIs[[':TYPE']] = dfCODESUIs[[':TYPE']].fillna(value='NA_UBKG')

# Merge and replace SUI:ID with name in CUI-SUIs.csv
# The UMLS version of SUIs.csv has name as a column.
dfCUISUIs = dfCUISUIs.merge(dfSUIs, how='inner', left_on=':END_ID', right_on='SUI:ID')
# neo4j-admin import looks for columns named :START_ID and :END_ID for relationship imports.
dfCUISUIs = dfCUISUIs[[':START_ID','name']]
dfCUISUIs.columns =[':START_ID', ':END_ID']

ulog.print_and_logger_info(f'Rewriting {csvCUISUIs}')
uextract.to_csv_with_progress_bar(df=dfCUISUIs, path=csvCUISUIs, index=False)

# Merge and replace SUI with name :END_ID with name in CODE-SUIs.csv.
# The UMLS version of SUIs.csv has name as a column.

dfCODESUIs = dfCODESUIs.merge(dfSUIs, how='inner', left_on=':END_ID', right_on='SUI:ID')
dfCODESUIs = dfCODESUIs[['name', ':START_ID', ':TYPE', 'CUI']]
# neo4j-admin import looks for columns named :START_ID and :END_ID for relationship imports.
dfCODESUIs.columns = [':END_ID', ':START_ID', ':TYPE', 'CUI']

ulog.print_and_logger_info(f'Rewriting {csvCODESUIs}')
uextract.to_csv_with_progress_bar(df=dfCODESUIs, path=csvCODESUIs, index=False)

# Replace SUI with name in SUIs.csv.
dfSUIs = dfSUIs[['name']]
# Format name as ID type.
dfSUIs.columns = ['name:ID']
ulog.print_and_logger_info(f'Rewriting {csvSUIs}')
uextract.to_csv_with_progress_bar(df=dfSUIs, path=csvSUIs, index=False)

