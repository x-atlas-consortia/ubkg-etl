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


# Import UBKG utilities which is in a directory that is at the same level as the script directory.
# Go "up and over" for an absolute path.
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath,'generation_framework/ubkg_utilities')
sys.path.append(fpath)
# Extraction module
import ubkg_extract as uextract
# Logging module
import ubkg_logging as ulog
import ubkg_config as uconfig
#-----------------------------

def download_source_files(cfg: uconfig.ubkgConfigParser, owl_dir: str, owlnets_dir: str) ->list[str]:
    # Obtains source files from GENCODE FTP site.

    # Returns a list of full paths to files extracted from downloaded files.
    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    # owl_dir - location of downloaded GenCode GZIP files
    # owlnets_dir - location of extracted GenCode GTF files

    # Create output folders for source files. Use the existing OWL and OWLNETS folder structure.
    os.system(f'mkdir -p {owl_dir}')
    os.system(f'mkdir -p {owlnets_dir}')

    # Download files specified in a list of URLs.
    list_gtf = []

    for key in cfg.config['URL']:
        url = cfg.get_value(section='URL',key=key)
        list_gtf.append(uextract.get_gzipped_file(url, owl_dir, owlnets_dir))

    return list_gtf

def load_GTF_into_DataFrame(file_pattern:str, path: str, skip_lines: int=0, rows_to_read: int=0) -> pd.DataFrame:

    # Loads a GTF file into a Pandas DataFrame, showing a progress bar.
    # file_pattern: portion of a name of a GTF file--e.g., "annotation"
    # path: path to folder containing GTF files.
    # skip_lines: number of lines to skip
    # rows_to_read: optional number of rows to read. In this case, the default means to read all rows.

    list_gtf = os.listdir(path)

    for filename in list_gtf:
        if file_pattern in filename:
            gtffile = os.path.join(path,filename)
            ulog.print_and_logger_info(f'Reading {gtffile}')
            return uextract.read_csv_with_progress_bar(path=gtffile,rows_to_read=rows_to_read,comment='#',sep='\t')

    ulog.print_and_logger_info(f'Error: missing file with name that includes \'{file_pattern}\'.')
    exit(1)

def build_key_value_column(dfGTFl1: pd.DataFrame, search_key: str):

    # Builds a consolidated value column from a key-value column in GTF format and adds it to the
    # input DataFrame.
    # Refer to https://www.gencodegenes.org/pages/data_format.html for the key-value column.

    # Arguments:
    # dfGTFl1- DataFrame of data downloaded from FTP, after the key-value column has been split by the
    #          Level 1 delimiter (colon)
    # search_key - name of the key to extract from the key-value column.
    # key_value_column - the key-value column from the DataFrame.

    # -----------------------------
    # Level 2 split
    # Split each column from the Level 1 split into key and value columns.
    listval = []

    for col in dfGTFl1:
        # The columns from the first-level split have names that are numbers starting with 0.
        if not isinstance(col, int):
            continue

        # Split each key/value pair column into separate key and value columns, using the space delimiter.
        # The strip function removes leading spaces that can be mistaken for delimiters, such as occurs in the
        # first key-value column.
        # Incorporate a progress bar.
        # tqdm.pandas(desc='splitting')
        dfSplit_level_2 = dfGTFl1[col].str.split(' ', expand=True).apply(lambda x: x.str.strip())

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
        dfValues = pd.concat(listval)

        # Concatenate multiple values that appear for the key in a row.
        # This collapses the result down to the correct number of rows.
        dfValues = dfValues.reset_index(names='rows')
        dfValues = dfValues.groupby('rows').agg({'value': lambda x: ','.join(x)})
        sValues = dfValues['value']
    else:
        # Return an empty series.
        sValues = pd.Series(index=dfGTFl1.index.copy(), dtype='str')

    # Add the consolidated list of values for the search key to the input DataFrame.
    dfGTFl1[search_key] = sValues

    return

def split_column9_level1(dfGTF: pd.DataFrame) ->pd.DataFrame:

    # Perform the first-level split of the key-value column (9th) of a GTF file, adding
    # separated key-value pairs as columns.

    # Refer to in-line documentation in the function build_Annotation_DataFrame for details on the
    # processing of the key-value column.

    key_value_column = dfGTF['column_9']

    # Split the key/value pairs using the colon delimiter.
    # Incorporate a progress bar.
    tqdm.pandas(desc='Splitting')
    dfSplit_level_1 = key_value_column.str.split(';', expand=True).progress_apply(lambda x: x.str.strip())

    # Normalize empty column empty values to NaN.
    dfSplit_level_1 = dfSplit_level_1.replace({'None': np.nan}).replace({None: np.nan}).replace({'': np.nan})
    # Remove completely empty columns.
    dfSplit_level_1 = dfSplit_level_1.dropna(axis=1, how='all')

    # Add columns of separated key-value pairs to the input.

    for col in dfSplit_level_1:
        dfGTF[col] = dfSplit_level_1[col]
    return dfGTF

def filter_Annotations(cfg: uconfig.ubkgConfigParser, df:pd.DataFrame)->pd.DataFrame:

    # Filters the annotation DataFrame by the types of annotations indicated in the application configuration file.
    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    # df: a DataFrame of annotation information.

    # Get desired feature types from the configuration file.
    feature_types = cfg.get_value(section='Filters',key='feature_types').split(',')
    if feature_types == ['all']:
        return df
    else:
        # Filter rows.
        return df[df['feature_type'].isin(feature_types)]

def filter_columns(cfg: uconfig.ubkgConfigParser, df:pd.DataFrame)->pd.DataFrame:

    # Reduces the set of columns in the annotation DataFrame by values indicated in the application configuration file.
    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    # df: a DataFrame of annotation information.

    cols = cfg.get_value(section='Filters',key='columns').split(',')
    if cols == ['all']:
        return df
    else:
        # Filter columns.
        df = df[cols]
        return df

def build_Annotation_DataFrame(cfg: uconfig.ubkgConfigParser, path: str) -> pd.DataFrame:

    # Builds a DataFrame that translates the GenCode annotation GTF file.
    # The specification of GTF files is at https://www.gencodegenes.org/pages/data_format.html

    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    # path: path to folder containing GTF files.

    # Load the "raw" version of the GTF file into a DataFrame.
    # Because the GenCode version is part of the file name (e.g., gencode.v41.annotation.gtf),
    # search on a file pattern.
    # The first five rows of the annotation file are comments.
    print('**********DEBUG: reading < total rows from annotation file.**********')
    dfGTF = load_GTF_into_DataFrame(file_pattern="annotation", path=path, skip_lines=5,rows_to_read=1000)

    # The GTF file does not have column headers. Add these with values from the specification.
    dfGTF.columns = cfg.get_value(section='GTF_columns',key='columns').split(',')
    # Filter annotation rows by types listed in configuration file.
    # This will likely reduce the size of the resulting DataFrame considerably.
    dfGTF = filter_Annotations(cfg=cfg, df=dfGTF)

    # Add columns corresponding to the key/value pairs in the 9th column.
    # GTF key names are from the specification.
    list_keys = cfg.get_value(section='GTF_column9_keys',key='keys').split(',')

    # --------------------------
    # The key-value column uses two levels of delimiting:
    # Level 1 - delimiter between key/value pairs = ;
    # Level 2 - delimiter between key and value = ' '

    # Excerpt of a key-value column (from the general annotation GTF):
    # "gene_id "ENSG00000223972.5"; transcript_id "ENST00000456328.2"; gene_type "transcribed_unprocessed_pseudogene"; gene_name "DDX11L1";"

    # Key/value pairs do not have static locations--i.e., a key/value pair may be in column X in one row and column Y
    # in another.
    # Furthermore, some keys have multiple values in the same row. For example, row 11 of the annotation shows tag "basic" in column 11
    # and tag "Ensembl_canonical" in column 12.
    #

    # This means that the key-value columns after the Level 1 split will resemble the following
    # (x, y, z, a are keys):
    #     columns
    # row       1         2         3       4
    # 0         x 20
    # 1         x 30
    # 2                    x 40
    # 3         a 99
    # 4         y 25       z 30     x 50    x 60 <--note multiple values for the x key

    # The desired result if search_key = x is a series of values corresponding to key=x,
    # sorted in the original row order, with multiple values collected into lists--e.g.,
    #  x
    # 0 20
    # 1 30
    # 2 40
    # 3
    # 4 50,60

    # Level 1 split
    ulog.print_and_logger_info('-- Splitting the key-value column (9th) of the annotation file into individual key-value columns...')

    dfGTF['column_9'] = dfGTF['column_9'].str.replace('"', '')
    dfGTF = split_column9_level1(dfGTF)

    # Level 2 split and collect
    ulog.print_and_logger_info('-- Collecting values from key-value columns...')
    for k in tqdm(list_keys,desc='Collecting'):
        build_key_value_column(dfGTF,k)

    # Remove intermediate Level 1 columns.
    droplabels = []
    for col in dfGTF:
        if isinstance(col, int):
            droplabels.append(col)
    dfGTF=dfGTF.drop(columns=droplabels)
    return dfGTF

def build_Metadata_DataFrame(file_pattern: str, path: str, column_headers: list[str]) ->pd.DataFrame:

    # Builds a DataFrame that translates one of the GenCode metadata files.
    # The specification of metadata files is at https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_41/_README.TXT

    # path: path to folder containing GTF files.
    # file_pattern: relevant portion of a filename.
    # [The GenCode version is part of the file name (e.g., gencode.v41.annotation.gtf), so search on the pattern.]

    # Load the "raw" version of the GTF file into a DataFrame.

    # search on a file pattern.
    dfGTF = load_GTF_into_DataFrame(file_pattern=file_pattern, path=path)
   # The GTF file does not have column headers. Add these with values from the specification.
    dfGTF.columns = column_headers

    return dfGTF

def buildTranslatedAnnotationDataFrame(cfg: uconfig.ubkgConfigParser,path: str)-> pd.DataFrame:

    # Builds a DataFrame that:
    # 1. Translates the annotation GTF file.
    # 2. Combines translated GTF annotation data with metadata, joining by transcript_id.

    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    # path - full path to source GTF file.

    # Read GTF files into DataFrames.

    ulog.print_and_logger_info('** BUILDING TRANSLATED GTF ANNOTATION FILE **')
    # Load and translate annotation file.
    dfAnnotation = build_Annotation_DataFrame(cfg=cfg, path=path)

    # Metadata
    # Entrez file
    dfEntrez = build_Metadata_DataFrame(file_pattern='EntrezGene', path=path,
                                        column_headers=['transcript_id', 'Entrez_Gene_id'])
    # RefSeq file
    dfReqSeq = build_Metadata_DataFrame(file_pattern='RefSeq', path=path,
                                        column_headers=['transcript_id', 'RefSeq_RNA_id', 'RefSeq_protein_id'])
    # SwissProt file
    dfSwissProt = build_Metadata_DataFrame(file_pattern='SwissProt', path=path,
                                           column_headers=['transcript_id', 'UNIPROTKB_SwissProt_AN',
                                                           'UNIPROTKB_SwissProt_AN2'])
    # TrEMBL file
    dfTrEMBL = build_Metadata_DataFrame(file_pattern='TrEMBL', path=path,
                                        column_headers=['transcript_id', 'UNIPROTKB_TrEMBL_AN', 'UNIPROTKB_TrEMBL_AN2'])

    # Join Metadata files to Annotation file.
    ulog.print_and_logger_info('-- Merging annotation and metadata.')
    dfAnnotation = dfAnnotation.merge(dfEntrez, how='left', on='transcript_id')
    dfAnnotation = dfAnnotation.merge(dfReqSeq, how='left', on='transcript_id')
    dfAnnotation = dfAnnotation.merge(dfSwissProt, how='left', on='transcript_id')
    dfAnnotation = dfAnnotation.merge(dfTrEMBL, how='left', on='transcript_id')

    # Filter output by columns as indicated in the configuration file.
    dfAnnotation = filter_columns(cfg=cfg,df=dfAnnotation)

    # Write translated annotation file.
    outfile_ann = os.path.join(path, 'TranslatedAnnotationGTF.csv')
    ulog.print_and_logger_info(f'-- Writing to {outfile_ann}')
    uextract.to_csv_with_progress_bar(df=dfAnnotation, path=outfile_ann)
    return dfAnnotation


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

# ---------------------------------
# START

debug_skip = False

# Read from config file
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/gencode/gencode.ini')
gencode_config = uconfig.ubkgConfigParser(cfgfile)

# Get OWL and OWLNETS directories.
# The config file should contain absolute paths to the directories.
owl_dir = os.path.join(os.path.dirname(os.getcwd()),gencode_config.get_value(section='Directories',key='owl_dir'))
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()),gencode_config.get_value(section='Directories',key='owlnets_dir'))

# Download and decompress GZIP files of GENCODE content from FTP site.
if debug_skip is True:
    print('Skipping download of source files from GenCode.')
else:
    lst_gtf = download_source_files(cfg=gencode_config, owl_dir=owl_dir,owlnets_dir=owlnets_dir)

# Build the DataFrame that combines translated GTF annotation data with metadata.
dfAnnotation = buildTranslatedAnnotationDataFrame(path=owlnets_dir,cfg=gencode_config)

# Generate edge file.
print('TO DO: Generate edge file.')
# Generate node file.
print('TO DO: Generate node file.')

# Debug exception to stop build_csv.sh.
raise Exception ("DEVELOPMENT: HALTING EXECUTION.")



