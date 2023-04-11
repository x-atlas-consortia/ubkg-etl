#!/usr/bin/env python
# coding: utf-8

# Unified Biomedical Knowledge Graph
# Script to ingest GenCode data

import os
import sys
import argparse

# Import the GZIP extraction module, which is in a directory that is at the same level as the script directory.
# Go "up and over" for an absolute path.
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath,'generation_framework/ubkg_utilities')
sys.path.append(fpath)
import ubkg_extract as uextract
import ubkg_logging as ulog

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

parser = argparse.ArgumentParser(
    description='Build .csv files from GenCode data files',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument("-o", "--owl_dir", type=str, default=os.path.join(os.path.dirname(os.getcwd()),'generation_framework/owl/GENCODE'),
                    help='directory to which to download and extract source files')
parser.add_argument("-l", "--owlnets_dir", type=str, default=os.path.join(os.path.dirname(os.getcwd()),'generation_framework/owlnets_output/GENCODE'),
                    help='directory containing the GenCode in OWLNETS format')
parser.add_argument("-s", "--skipExtract", action="store_true",
                    help='skip the download of the FTPs')
args = parser.parse_args()

# Download and decompress files.

os.system(f'mkdir -p {args.owl_dir}')
os.system(f'mkdir -p {args.owlnets_dir}')

# Get list of files to download.
fpath = os.path.join(os.getcwd(),'gencode/ftplist.txt')
with open(fpath,'r') as fconfig:
    listurl=[]
    for furl in fconfig:
        listurl.append(furl)
fconfig.close()

for u in listurl:
    uextract.get_gzipped_file(u,args.owl_dir,args.owlnets_dir)

raise Exception ("DEBUG")

#---


