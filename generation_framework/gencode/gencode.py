#!/usr/bin/env python
# coding: utf-8

# Unified Biomedical Knowledge Graph
# Script to ingest GenCode data

import os
import sys
import argparse
from tqdm import tqdm
import pandas as pd
import numpy as np


# Import the GZIP extraction module, which is in a directory that is at the same level as the script directory.
# Go "up and over" for an absolute path.
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath,'generation_framework/ubkg_utilities')
sys.path.append(fpath)
import ubkg_extract as uextract
import ubkg_logging as ulog

#-----------------------------

def get_source_files(owl_dir: str, owlnets_dir: str)-> list[str]:
    # Obtains source files from GENCODE FTP site.

    # Returns a list of full paths to files extracted from downloaded files.

    # Create output folders for source files. Use the existing OWL and OWLNETS folder structure.
    os.system(f'mkdir -p {owl_dir}')
    os.system(f'mkdir -p {owlnets_dir}')

    # Download files specified in a list of URLs.
    fpath = os.path.join(os.getcwd(), 'gencode/gencode_urls.txt')
    try:
        with open(fpath, 'r') as fgencodeurl:
            Lines = fgencodeurl
            list_gtf = []
            for line in Lines:
                url = line.strip()
                list_gtf.append(uextract.get_gzipped_file(url, owl_dir, owlnets_dir))

    except FileNotFoundError as e:
        ulog.print_and_logger_info(
            'Missing file of URLs of files to download named \'gencode_urls.txt\'.')
        exit(1)


    return list_gtf

def load_GTF_into_DataFrame(file_pattern:str, path: str, skip_lines:int=0) -> pd.DataFrame:

    # Loads a GTF file into a Pandas DataFrame.
    # file_pattern: portion of a name of a GTF file--e.g., "annotation"
    # path: path to folder containing GTF files.
    # skip_lines: number of lines to skip

    list_gtf = os.listdir(path)

    for filename in list_gtf:
        if file_pattern in filename:
            gtffile = os.path.join(path,filename)
            ulog.print_and_logger_info(f'Loading {gtffile} into Pandas.')

            # Get number of lines in file.
            with open(gtffile, 'r') as fp:
                lines = len(fp.readlines())
            # Read file in chunks, updating progress bar after each chunk.
            listdf = []
            with tqdm(total=lines,desc='Loading file') as bar:
                for chunk in pd.read_csv(gtffile,chunksize=1000,comment='#',sep='\t',nrows=5):
                    listdf.append(chunk)
                    bar.update(chunk.shape[0])

            df = pd.concat(listdf,axis=0,ignore_index=True)
            return df

    ulog.print_and_logger_info(f'Error: missing file with name that includes \'{file_pattern}\'.')
    exit(1)


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass



# ---------------------------------
# START

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

# Download and decompress GZIP files of GENCODE content from FTP site.
if args.skipExtract is True:
    ulog.print_and_logger_info('Skipping download of source files from GenCode.')
    list_gtf = os.listdir(args.owlnets_dir)
else:
    list_gtf = get_source_files(args.owl_dir,args.owlnets_dir)


# Read GTF files into DataFrames.
dfAnnotation = load_GTF_into_DataFrame(file_pattern="annotation",path=args.owlnets_dir,skip_lines=5)
dfAnnotation.columns=['chromosome_name','annotation_source','feature_type','genomic_start_location','genomic_end_location','score','genomic_strand','genomic_phase','column_9']

print(dfAnnotation)


raise Exception ("DEBUG")

#---


