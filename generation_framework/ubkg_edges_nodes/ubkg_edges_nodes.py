#!/usr/bin/env python
# coding: utf-8

# Copies a set of UBKG ingestion files in UBKG edges/nodes format from a specified local directory to the appropriate
# directory in the local repo.

import argparse
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
# Config file
import ubkg_config as uconfig
# Calling subprocesses
import ubkg_subprocess as usub

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

def containsEdgeNodeFiles(path: str)->bool:
    # Checks files in a local path.

    # Files should be one of two types:
    # 1. Edges/nodes files
    # 2. An OWL file

    isedge = False
    for f in os.listdir(path):
        fpath = os.path.join(path, f)
        if os.path.isfile(fpath):
            dfTest = pd.read_csv(os.path.join(frompath, f), sep='\t', nrows=5)
            if 'subject' in dfTest.columns or 'node_id' in dfTest.columns or 'relation_id' in dfTest.columns:
                isedge = True

    return isedge

def getOWLfilename(path: str)->str:
    #Returns the first file in a path, under the assumption that the directory contains a single OWL file.
    for f in os.listdir(path):
        fpath = os.path.join(path, f)
        if os.path.isfile(fpath):
            return f

# -----------------------------------------
# START

OWLNETS_SCRIPT = os.path.join(os.path.dirname(os.getcwd()),'generation_framework/owlnets_script/__main__.py')

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
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()),config.get_value(section='Directories',key='owlnets_dir'))
print(args.sab)
owlnets_dir_sab=os.path.join(owlnets_dir,args.sab)
owl_dir = os.path.join(os.path.dirname(os.getcwd()),config.get_value(section='Directories',key='owl_dir'))
owl_dir_sab=os.path.join(owl_dir,args.sab)
# Make the subdirectories.
os.system(f'mkdir -p {owlnets_dir_sab}')
os.system(f'mkdir -p {owl_dir_sab}')

# Get the appropriate file path.
frompath = config.get_value(section='Paths',key=args.sab)

if containsEdgeNodeFiles(frompath):
    # Copy files from the local path to the owlnets path.
    ulog.print_and_logger_info(f'Files in {frompath} are in edges/nodes format: copying to {owlnets_dir_sab}')
    os.system(f'cp {frompath}/*.* {owlnets_dir_sab}')
else:
    # Assume the folder contains a single OWL file that should be converted to OWLNETS format.
    ulog.print_and_logger_info(f'Files in {frompath} are not in edges/nodes format. Assuming that the file is an OWL.')
    os.system(f'cp {frompath}/*.* {owl_dir_sab}')
    url = os.path.join(owl_dir_sab, getOWLfilename(frompath))
    # Call OWLNETS script using the path to the local copy of the OWL file as the url.
    owlnets_script= f"{OWLNETS_SCRIPT} --ignore_owl_md5 -l {owlnets_dir} -o {owl_dir} {url} {args.sab}"
    ulog.print_and_logger_info(f"Running: {owlnets_script}")
    usub.call_subprocess(owlnets_script)
