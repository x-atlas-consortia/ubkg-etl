#!/usr/bin/env python
# coding: utf-8

# JULY 2023
# Script that initializes the set of UMLS CSVs extracted from the Neptune data warehouse.

import sys
import os

# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path. (This assumes that this script is being called from build_csv.py.)
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)

# Logging module
import ubkg_logging as ulog
# Extracting files
import ubkg_extract as uextract
import ubkg_parsetools as uparse
# Config file
import ubkg_config as uconfig

# ------------------

print('in script')
# Read from config file.
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'umls_init.ini')
config = uconfig.ubkgConfigParser(cfgfile)
# Obtain the CSV directory path.
csvdir = uconfig.get_value(section='Directory', key='csvdir')
print(csvdir)