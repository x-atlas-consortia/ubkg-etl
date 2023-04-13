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

    # Loads a GTF file into a Pandas DataFrame, showing a progress bar.
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
                for chunk in pd.read_csv(gtffile,chunksize=1000,comment='#',sep='\t',nrows=100):
                    listdf.append(chunk)
                    bar.update(chunk.shape[0])

            df = pd.concat(listdf,axis=0,ignore_index=True)

            return df

    ulog.print_and_logger_info(f'Error: missing file with name that includes \'{file_pattern}\'.')
    exit(1)

def get_key_value_column(search_key: str, key_value_column: pd.Series) -> pd.Series:

    # Returns a consolidated value column from a key-value column in GTF format.
    # Refer to https://www.gencodegenes.org/pages/data_format.html for the key-value column.

    # Arguments:
    # search_key - name of the key to extract from the key-value column.
    # key_value_column - the key-value column from the DataFrame.

    # --------------------------
    # The key-value column uses two levels of delimiting:
    # Level 1 - delimiter between key/value pairs = ;
    # Level 2 - delimiter between key and value = ' '

    # Excerpt of a key-value column (from the general annotation GTF):
    # "gene_id "ENSG00000223972.5"; transcript_id "ENST00000456328.2"; gene_type "transcribed_unprocessed_pseudogene"; gene_name "DDX11L1";"

    # Key/value pairs do not have static locations--i.e., a key/value pair may be in column X in one row and column Y
    # in another.
    # Furthermore, some keys have multiple values in the same row--e.g., tag, ont.
    # For example, row 11 of the annotation shows tag "basic" in column 11 and tag "Ensembl_canonical" in column 12.
    #
    # Build a series of values for a particular key by looking through all columns.

    # Example (x, y, z, a are keys):
    #     columns
    # row       1         2         3       4
    # 0         x 20
    # 1         x 30
    # 2                    x 40
    # 3         a 99
    # 4         y 25       z 30     x 50    x 60 <--note multiple values for x

    # The desired result if search_key = x is a series of values corresponding to key=x, sorted in the original order
    # of the argument series:
    # 0 20
    # 1 30
    # 2 40
    # 3
    # 4 50,60

    # -----------------------------

    # Level 1 split
    # Split the key/value pairs using the colon delimiter.
    dfSplit_level_1 = key_value_column.str.split(';', expand=True)
    # Normalize empty column empty values to NaN.
    dfSplit_level_1 = dfSplit_level_1.replace({'None': np.nan}).replace({None: np.nan}).replace({'': np.nan})
    # Remove completely empty columns.
    dfSplit_level_1 = dfSplit_level_1.dropna(axis=1, how='all')


    # Level 2 split
    # Split each column from the Level 1 split into key and value columns.

    listval = []
    for col in dfSplit_level_1:

        # Split each key/value pair column into separate key and value columns, using the space delimiter.
        # The strip function removes leading spaces that can be mistaken for delimiters.
        dfSplit_level_2 = dfSplit_level_1[col].str.strip()
        dfSplit_level_2 = dfSplit_level_2.str.split(' ', expand=True)
        # The split gives the key and value columns numeric names. Rename for clarity.
        dfSplit_level_2.columns = ['key','value']

        # Obtain values that correspond to the search key
        # In general, there are multiple values for a key on a row, so there will be multiple rows in the
        # dataframe with the same index value.
        dfSplit_level_2 = dfSplit_level_2[dfSplit_level_2['key'] == search_key]

        # Add any matching values to the set, organized by index.
        if dfSplit_level_2.shape[0] > 0:
            listval.append(dfSplit_level_2)

    if len(listval) > 0:
        # Build the entire list of values for the key.
        dfReturn = pd.concat(listval)

        # Concatenate multiple values that appear for the key in a row.
        # This collapses the result down to the correct number of rows.
        dfReturn = dfReturn.reset_index(names='rows')
        dfReturn = dfReturn.groupby('rows').agg({'value': lambda x: ','.join(x)})
        sReturn = dfReturn['value']
    else:
        # Return an empty series.
        sReturn = pd.Series(index=key_value_column.index.copy(), dtype='str')

    return sReturn

def build_Annotation_DataFrame(path: str) -> pd.DataFrame:

    # Builds a DataFrame that translates the GenCode annotation GTF file.
    # The specification of GTF files is at https://www.gencodegenes.org/pages/data_format.html

    # path: path to folder containing GTF files.

    # Load the "raw" version of the GTF file into a DataFrame.
    # Because the GenCode version is part of the file name (e.g., gencode.v41.annotation.gtf),
    # search on a file pattern.
    # The first five rows of the annotation file are comments.
    df = load_GTF_into_DataFrame(file_pattern="annotation", path=args.owlnets_dir, skip_lines=5)

    # Add column headers.
    df.columns = ['chromosome_name', 'annotation_source', 'feature_type', 'genomic_start_location',
                              'genomic_end_location', 'score', 'genomic_strand', 'genomic_phase', 'column_9']

    # Add columns corresponding to the key/value pairs in the 9th column.
    # GTF keys.
    list_keys = [
        # required
        'gene_id',
        'transcript_id',
        'gene_type',
        'gene_status',
        'gene_name',
        'transcript_type',
        'transcript_status',
        'transcript_name',
        'exon_number',
        'exon_id',
        'level',
        # optional
        'tag',
        'ccdsid',
        'havana_gene',
        'havana_transcript',
        'protein_id',
        'ont',
        'transcript_support_level',
        'remap_status',
        'remap_original_id',
        'remap_original_location',
        'remap_num_mappings',
        'remap_target_status',
        'remap_substituted_missing_target',
        'hgnc_id',
        'mgi_id'
    ]

    df['column_9'] = df['column_9'].str.replace('"', '')
    for k in list_keys:
        df[k] = get_key_value_column(k, df['column_9'])

    return df

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

# 1. Annotation file
dfAnnotation = build_Annotation_DataFrame(path=args.owlnets_dir)

# TO DO
# 2. Entrez file

# Join Entrez file to Annotation file.

# Generate edge file.
# Generate node file.

# Debug exception to stop build_csv.sh.
raise Exception ("DEBUG")

#---


