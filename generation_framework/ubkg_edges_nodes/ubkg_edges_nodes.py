#!/usr/bin/env python
# coding: utf-8

# Copies a set of UBKG ingestion files in UBKG edges/nodes format from a specified local directory to the appropriate
# directory in the local repo.

import argparse
import sys
import os

# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path. (This assumes that this script is being called from build_csv.py.)
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)

# Logging module
import ubkg_logging as ulog
# Config file
import ubkg_config as uconfig

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

# -----------------------------------------
# START

parser = argparse.ArgumentParser(
    description='Copies ingest files in UBKG edges/nodes format from a local directory.',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument('sab', help='SAB for ingest files')
args = parser.parse_args()

# Read from config file.
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/ubkg_edges_nodes/edges_nodes.ini')
config = uconfig.ubkgConfigParser(cfgfile)

# Get OWLNETS directory.
# The config file contains absolute paths to the parent directories in the local repo.
# Affix the SAB to the paths.
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()),config.get_value(section='Directories',key='owlnets_dir'),args.sab)

# Make the subdirectory.
os.system(f'mkdir -p {owlnets_dir}')

# Get the appropriate file path.
frompath = config.get_value(section='Paths',key=args.sab)

# Copy files from the local path to the owlnets path.
os.system(f'cp {frompath}/*.* {owlnets_dir}')
ulog.print_and_logger_info(f'Copied files from {frompath} to {owlnets_dir}')
