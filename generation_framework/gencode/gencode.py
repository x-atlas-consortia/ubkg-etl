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
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)
# Extraction module
import ubkg_extract as uextract
# Logging module
import ubkg_logging as ulog
import ubkg_config as uconfig
# -----------------------------


def download_source_files(cfg: uconfig.ubkgConfigParser, owl_dir: str, owlnets_dir: str) -> list[str]:
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
        url = cfg.get_value(section='URL', key=key)
        # The URL contains the filename.
        zipfilename = url.split('/')[-1]
        list_gtf.append(uextract.get_gzipped_file(gzip_url=url, zip_path=owl_dir, extract_path=owlnets_dir, zipfilename=zipfilename))

    return list_gtf


def load_GTF_into_DataFrame(file_pattern: str, path: str, skip_lines: int=0, rows_to_read: int=0) -> pd.DataFrame:

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
            return uextract.read_csv_with_progress_bar(path=gtffile, rows_to_read=rows_to_read, comment='#',sep='\t')

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


def split_column9_level1(dfGTF: pd.DataFrame) -> pd.DataFrame:

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


def filter_Annotations(cfg: uconfig.ubkgConfigParser, df: pd.DataFrame) -> pd.DataFrame:

    # Filters the annotation DataFrame by the types of annotations indicated in the application configuration file.
    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    # df: a DataFrame of annotation information.

    # Get desired feature types from the configuration file.
    feature_types = cfg.get_value(section='Filters', key='feature_types').split(',')
    if feature_types == ['all']:
        return df
    else:
        # Filter rows.
        return df[df['feature_type'].isin(feature_types)]


def filter_columns(cfg: uconfig.ubkgConfigParser, df: pd.DataFrame) -> pd.DataFrame:

    # Reduces the set of columns in the annotation DataFrame by values indicated in the application configuration file.
    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    # df: a DataFrame of annotation information.

    cols = cfg.get_value(section='Filters', key='columns').split(',')
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

    dfGTF = load_GTF_into_DataFrame(file_pattern="annotation", path=path, skip_lines=5)

    # The GTF file does not have column headers. Add these with values from the specification.
    dfGTF.columns = cfg.get_value(section='GTF_columns', key='columns').split(',')
    # Filter annotation rows by types listed in configuration file.
    # This will likely reduce the size of the resulting DataFrame considerably.
    dfGTF = filter_Annotations(cfg=cfg, df=dfGTF)

    # Add columns corresponding to the key/value pairs in the 9th column.
    # GTF key names are from the specification.
    list_keys = cfg.get_value(section='GTF_column9_keys', key='keys').split(',')

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
    for k in tqdm(list_keys, desc='Collecting'):
        build_key_value_column(dfGTF, k)

    # Remove intermediate Level 1 columns.
    droplabels = []
    for col in dfGTF:
        if isinstance(col, int):
            droplabels.append(col)
    dfGTF = dfGTF.drop(columns=droplabels)
    return dfGTF

def build_Metadata_DataFrame(file_pattern: str, path: str, column_headers: list[str]) -> pd.DataFrame:

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


def buildTranslatedAnnotationDataFrame(cfg: uconfig.ubkgConfigParser, path: str, outfile: str) -> pd.DataFrame:

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
    dfAnnotation = filter_columns(cfg=cfg, df=dfAnnotation)

    # Write translated annotation file.
    outfile_ann = os.path.join(path, outfile)
    ulog.print_and_logger_info(f'-- Writing to {outfile_ann}')
    uextract.to_csv_with_progress_bar(df=dfAnnotation, path=outfile_ann)
    return dfAnnotation


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


def getargs() -> argparse.Namespace:

    # Parse arguments.
    parser = argparse.ArgumentParser(
    description='Convert the GZipped CSV file of the ontology to OWLNETs.\n'
                'In general you should not have the change any of the optional arguments.',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
    # positional arguments
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")
    args = parser.parse_args()

    return args


def write_edges_file(df: pd.DataFrame, path: str, ont_path: str):

    # Translates the content of a GTF annotation file to OWLNETS format.
    # df - DataFrame of annotated GTF information.
    # path - export path of OWLNETS files
    # ont_path - path to the directory containing OWLNETS files related to the ingestion of the GENCODE_ONT ontology

    # Assertions on transcripts:
    # - transcribed from genes, using Ensembl IDs for genes
    # - has proteins as gene products, using the UNIPROTKB IDs

    # The object node IDs for assertions for which subjects are features are obtained from the
    # OWLNETS_node_metadata file for the GENCODE_ONT set of assertions.
    # Feature assertions:
    # 1. Feature is located in a chromosome
    # 2. Feature has feature type
    # 3. Feature has biotype, based on whether the feature is a gene (gene_type) or not (transcript_type)
    # 4. Feature has directional form (strand direction)
    # 5. Feature isa for all PGO codes in the ont field

    # Read the node information from GENCODE_ONT.
    dfGenCode_ont = getGenCodeOnt(path=ont_path)

    edgelist_path: str = os.path.join(path, 'OWLNETS_edgelist.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(edgelist_path))

    with open(edgelist_path, 'w') as out:
        # header
        out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')

        # ASSERTIONS FOR TRANSCRIPTS
        ulog.print_and_logger_info('Writing \'transcribed from\' and \'has gene product\' edges for transcripts')
        # Identify unique transcript IDs.
        dftranscript = df[df['feature_type'] == 'transcript']
        dftranscript = dftranscript.drop_duplicates(subset=['transcript_id']).reset_index(drop=True)

        # Show TQDM progress bar.
        for index, row in tqdm(dftranscript.iterrows(), total=dftranscript.shape[0]):
            subject = 'ENSEMBL:' + row['transcript_id']
            object = 'ENSEMBL:' + row['gene_id']


            # ASSERTION: transcribed_from
            predicate = 'http://purl.obolibrary.org/obo/RO_0002510' # transcribed from
            out.write(subject + '\t' + predicate + '\t' + object + '\n')

            # ASSERTIONs: has_gene_product
            # Look for proteins in both SwissProt and Trembl annotations of UniProtKB
            predicate = 'http://purl.obolibrary.org/obo/RO_0002205' # has_gene_product
            if row['UNIPROTKB_SwissProt_AN'] != '':
                object = 'UNINPROTKB:'+ row['UNIPROTKB_SwissProt_AN']
                out.write(subject + '\t' + predicate + '\t' + object + '\n')

            if row['UNIPROTKB_TrEMBL_AN'] != '':
                object = 'UNIPROTKB:' + row['UNIPROTKB_TrEMBL_AN']
                out.write(subject + '\t' + predicate + '\t' + object + '\n')

        # ASSERTIONS for features (genes, transcripts, etc.)
        ulog.print_and_logger_info('Writing edges for all features (gene, transcript, etc.)--chromosome, biotype, direction, pseudogene, RefSeq')
        for index, row in tqdm(df.iterrows(), total=df.shape[0]):

            # feature ID
            if row['transcript_id'] != '':
                subject = 'ENSEMBL:' + row['transcript_id']
            else:
                subject = 'ENSEMBL:' + row['gene_id']

            object = ''

            # Assertion: (feature) located in (chromosome)
            predicate = 'http://purl.obolibrary.org/obo/RO_0001025' # located in
            # Obtain from GENCODE_ONT the node_id for the node that corresponds
            # to the value from the chromosome_name column.
            if dfGenCode_ont.loc[dfGenCode_ont['node_label']==row['chromosome_name'],'node_id'].shape[0] > 0:
                object = str(dfGenCode_ont.loc[dfGenCode_ont['node_label']==row['chromosome_name'],'node_id'].iat[0])
                if object !='':
                    out.write(subject + '\t' + predicate + '\t' + object + '\n')

            object = ''
            # Assertion: (feature) has feature type (feature type)
            # There is currently no appropriate relation property in RO.
            predicate = 'is feature type'
            # Obtain from GENCODE_ONT the node_id for the feature type
            if dfGenCode_ont.loc[dfGenCode_ont['node_label'] == row['feature_type'], 'node_id'].shape[0] > 0:
                object = str(dfGenCode_ont.loc[dfGenCode_ont['node_label'] == row['feature_type'], 'node_id'].iat[0])
                if object !='':
                    out.write(subject + '\t' + predicate + '\t' + object + '\n')

            object = ''
            # Assertion: (feature) is gene biotype
            # There is currently no appropriate relation property in RO.
            predicate = 'is gene biotype'
            if row['gene_type'] != '':
                if dfGenCode_ont.loc[dfGenCode_ont['node_label'] == row['gene_type'], 'node_id'].shape[0] >0:
                    object = str(dfGenCode_ont.loc[dfGenCode_ont['node_label'] == row['gene_type'], 'node_id'].iat[0])
                    if object !='':
                        out.write(subject + '\t' + predicate + '\t' + object + '\n')

            object = ''
            # Assertion: (feature) is transcript biotype
            # There is currently no appropriate relation property in RO.
            predicate = 'is transcript biotype'
            if row['transcript_type'] != '':
                if dfGenCode_ont.loc[dfGenCode_ont['node_label'] == row['transcript_type'], 'node_id'].shape[0] > 0:
                    object = str(dfGenCode_ont.loc[dfGenCode_ont['node_label'] == row['transcript_type'], 'node_id'].iat[0])
                if object != '':
                    out.write(subject + '\t' + predicate + '\t' + object + '\n')

            object = ''
            # Assertion: (feature) has directional form of (strand)
            predicate ='http://purl.obolibrary.org/obo/RO_0004048' # has directional form of
            if row['genomic_strand'] == '+':
                direction = 'positive'
            if row['genomic_strand'] == '-':
                direction = 'negative'
            if direction != '':
                if dfGenCode_ont.loc[dfGenCode_ont['node_label'] == direction, 'node_id'].shape[0] > 0:
                    object = str(dfGenCode_ont.loc[dfGenCode_ont['node_label'] == direction, 'node_id'].iat[0])
            if object !='':
                out.write(subject + '\t' + predicate + '\t' + object + '\n')

            object = ''
            # Assertion: isa (type of Pseudogene)
            # Assume that the ont field can be a list of PGO IDs.
            predicate = 'subClassOf'
            if row['ont'] != '':
                listPGO = row['ont'].split(',')
                for pgo in listPGO:
                    if dfGenCode_ont.loc[dfGenCode_ont['node_label'] == pgo, 'node_id'].shape[0] > 0:
                        object = dfGenCode_ont.loc[dfGenCode_ont['node_label'] == pgo, 'node_id'].iat[0]
                    if object !='':
                        out.write(subject + '\t' + predicate + '\t' + pgo + '\n')

            object = ''
            # Assertion: has refSeq ID
            predicate = 'has refSeq ID'
            if row['RefSeq_RNA_id'] != '':
                if dfGenCode_ont.loc[dfGenCode_ont['node_label'] == row['RefSeq_RNA_id'], 'node_id'].shape[0] > 0:
                    object = 'REFSEQ:' + dfGenCode_ont.loc[dfGenCode_ont['node_label'] == row['RefSeq_RNA_id'], 'node_id'].iat[0]
                if object != '':
                    out.write(subject + '\t' + predicate + '\t' + pgo + '\n')

    return

def write_nodes_file(df: pd.DataFrame, path: str):

    # Writes a nodes file in OWLNETS format.
    # Arguments:
    # df - DataFrame of source information
    # path: output directory

    # The primary annotation nodes information is the set of cross-references, including:
    # - HGNC and Entrez IDs for Ensembl gene IDs
    # - RefSeq RNA IDs for transcripts

    # The Entrez IDs for genes are associated with the gene's transcripts. The Entrez ID is the same for all
    # of a gene's transcripts.

    node_metadata_path: str = os.path.join(owlnets_dir, 'OWLNETS_node_metadata.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(node_metadata_path))

    # Get subsets of annotations by feature type.
    # gene
    dfgene = df[df['feature_type'] == 'gene']
    dfgene = dfgene.drop_duplicates(subset=['gene_id']).reset_index(drop=True)
    dfgene = dfgene.replace(np.nan, '')
    # transcript
    dftranscript = df[df['feature_type'] == 'transcript']
    dftranscript = dftranscript.drop_duplicates(subset=['transcript_id']).reset_index(drop=True)
    dftranscript = dftranscript.replace(np.nan, '')

    with open(node_metadata_path, 'w') as out:
        out.write(
            'node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_definition' + '\t' +
            'node_synonyms' + '\t' + 'node_dbxrefs' + '\t' + 'value' + '\t' + 'lowerbound' + '\t' +
            'upperbound' + '\t' + 'unit' + '\n')

        # GENE NODES
        ulog.print_and_logger_info('Writing gene nodes')
        # Find unique gene nodes.

        # Show TQDM progress bar.
        for index, row in tqdm(dfgene.iterrows(), total=dfgene.shape[0]):
            node_id = 'ENSEMBL:' + row['gene_id']
            node_namespace = 'GENCODE'
            node_label = row['gene_name'].strip()

            node_definition = ''
            node_synonyms = ''

            dbxreflist = []
            if row['hgnc_id'] != '':
                dbxreflist.append('HGNC ' + row['hgnc_id'])
            if row['mgi_id'] != '':
                dbxreflist.append('MGI:' + row['mgi_id'])


            node_dbxrefs = ''
            if len(dbxreflist) > 0:
                node_dbxrefs = '|'.join(dbxreflist)

            value = ''
            lowerbound = str(int(row['genomic_start_location']))
            upperbound = str(int(row['genomic_end_location']))
            unit = ''

            out.write(
                node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t'
                + node_synonyms + '\t' + node_dbxrefs + '\t' + value + '\t' + lowerbound + '\t' + upperbound + '\t' + unit + '\n')

        # TRANSCRIPT NODES
        # Group by transcript_id and RefSeq_RNA_id.
        ulog.print_and_logger_info('Writing transcript nodes')

        for index, row in tqdm(dftranscript.iterrows(), total=dftranscript.shape[0]):
            node_id = 'ENSEMBL:' + row['transcript_id']
            node_namespace = 'GENCODE'
            node_label = row['transcript_name']
            node_definition = ''
            node_synonyms = ''
            value = ''
            lowerbound = str(int(row['genomic_start_location']))
            upperbound = str(int(row['genomic_end_location']))
            unit = ''
            node_dbxrefs = ''

            out.write(node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t'
                      + node_synonyms + '\t' + node_dbxrefs + '\t' + value + '\t' + lowerbound + '\t' + upperbound + '\t' + unit + '\n')

        # ENTREZ GENE NODES
        # These are available in the annotation file, but are not involved in edges.
        # Map them to HGNC IDs.
        ulog.print_and_logger_info('Writing Entrez nodes')

        dfEntrez = dftranscript[dftranscript['Entrez_Gene_id']!='']
        dfEntrez = dfEntrez.drop_duplicates(subset=['Entrez_Gene_id']).reset_index(drop=True)
        for index, row in tqdm(dfEntrez.iterrows(), total=dfEntrez.shape[0]):
            node_id = 'ENTREZ:' + str(int(row['Entrez_Gene_id']))
            node_namespace = 'GENCODE'
            node_label = row['gene_name']
            node_definition = ''
            node_synonyms = ''
            value = ''
            lowerbound = str(int(row['genomic_start_location']))
            upperbound = str(int(row['genomic_end_location']))
            unit = ''
            node_dbxrefs = 'HGNC ' + row['hgnc_id']
            out.write(node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t'
                      + node_synonyms + '\t' + node_dbxrefs + '\t' + value + '\t' + lowerbound + '\t' + upperbound + '\t' + unit + '\n')

        # REFSEQ NODES
        # These are available in the annotation file.
        ulog.print_and_logger_info('Writing RefSeq nodes')
        dfRefSeq = df[df['RefSeq_RNA_id'] != '']
        dfRefSeq = dfRefSeq.drop_duplicates(subset=['RefSeq_RNA_id']).reset_index(drop=True)
        for index, row in tqdm(dfRefSeq.iterrows(), total=dfRefSeq.shape[0]):
            node_id = 'REFSEQ:' + (row['RefSeq_RNA_id'])
            node_namespace = 'GENCODE'
            node_label = row['RefSeq_RNA_id']
            node_definition = ''
            node_synonyms = ''
            value = ''
            lowerbound = ''
            upperbound = ''
            unit = ''
            node_dbxrefs = ''
            out.write(node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t'
                      + node_synonyms + '\t' + node_dbxrefs + '\t' + value + '\t' + lowerbound + '\t' + upperbound + '\t' + unit + '\n')

    return

def write_relations_file(path: str):

    # Writes a relations file in OWLNETS format.
    # Arguments:
    # df - DataFrame of source information
    # owlnets_dir: output directory

    # RELATION METADATA
    # Create a row for each type of relationship.

    relation_path: str = os.path.join(path, 'OWLNETS_relations.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(relation_path))

    with open(relation_path, 'w') as out:
        # header
        out.write(
            'relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\t' + 'relation_definition' + '\n')
        relation1_id = 'http://purl.obolibrary.org/obo/RO_0002510' # transcribed from
        relation1_label = 'transcribed from'
        relation2_id = 'http://purl.obolibrary.org/obo/RO_0002205' # has_gene_product
        relation2_label='has gene product'
        relation3_id = 'http://purl.obolibrary.org/obo/RO_0001025'  # located in
        relation3_label = 'located in'
        relation4_id = 'is gene biotype'
        relation4_label ='is gene biotype'
        relation5_id = 'is transcript biotype'
        relation5_label = 'is transcript biotype'
        relation6_id = 'http://purl.obolibrary.org/obo/RO_0004048' # has directional form of
        relation6_label = 'has directional form of'
        relation7_id = 'subclassOf'
        relation7_label = 'subClassOf'
        relation8_id = 'has refSeq ID'
        relation8_label = 'has refSeq ID'

        out.write(relation1_id + '\t' + 'GENCODE' + '\t' + relation1_label + '\t' + '' + '\n')
        out.write(relation2_id + '\t' + 'GENCODE' + '\t' + relation2_label + '\t' + '' + '\n')
        out.write(relation3_id + '\t' + 'GENCODE' + '\t' + relation3_label + '\t' + '' + '\n')
        out.write(relation4_id + '\t' + 'GENCODE' + '\t' + relation4_label + '\t' + '' + '\n')
        out.write(relation5_id + '\t' + 'GENCODE' + '\t' + relation5_label + '\t' + '' + '\n')
        out.write(relation6_id + '\t' + 'GENCODE' + '\t' + relation6_label + '\t' + '' + '\n')
        out.write(relation7_id + '\t' + 'GENCODE' + '\t' + relation7_label + '\t' + '' + '\n')
        out.write(relation8_id + '\t' + 'GENCODE' + '\t' + relation8_label + '\t' + '' + '\n')

    return


def getGenCodeOnt(path: str) -> pd.DataFrame:

    # The GENCODE annotation file has columns with values that have been encoded as nodes in the GENCODE_ONT
    # set of assertions.
    # Load the nodes file related to the prior ingestion.

    nodefile = os.path.join(path, 'OWLNETS_node_metadata.txt')

    try:
        return uextract.read_csv_with_progress_bar(nodefile, sep='\t')
    except FileNotFoundError:
        ulog.print_and_logger_info('GENCODE depends on the prior ingestion of information '
                                   'from the GENCODE_ONT SAB. Run .build_csv.sh for GENCODE_ONT prior '
                                   'to running it for GENCODE.')
        exit(1)

# ---------------------------------
# START


args = getargs()

# Read from config file
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/gencode/gencode.ini')
gencode_config = uconfig.ubkgConfigParser(cfgfile)

# Get OWL and OWLNETS directories.
# The config file should contain absolute paths to the directories.
owl_dir = os.path.join(os.path.dirname(os.getcwd()), gencode_config.get_value(section='Directories', key='owl_dir'))
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()), gencode_config.get_value(section='Directories', key='owlnets_dir'))

# Obtain the path to the OWLNETS files that correspond to the application ontology information for GenCode.
ont_dir = os.path.join(os.path.dirname(os.getcwd()),gencode_config.get_value(section='Directories',key='lookup_dir'))

# Obtain output name for the translated annotation file.
ann_file = gencode_config.get_value(section='AnnotationFile',key='filename')

if args.skipbuild:
    # Read previously generated annotation CSV.
    path = os.path.join(owlnets_dir, ann_file)
    dfAnnotation = uextract.read_csv_with_progress_bar(path=path, rows_to_read=1000)
    dfAnnotation = dfAnnotation.replace(np.nan, '')
else:
    # Download and decompress GZIP files of GENCODE content from FTP site.
    lst_gtf = download_source_files(cfg=gencode_config, owl_dir=owl_dir, owlnets_dir=owlnets_dir)
    # Build the DataFrame that combines translated GTF annotation data with metadata.
    dfAnnotation = buildTranslatedAnnotationDataFrame(path=owlnets_dir, cfg=gencode_config, outfile=ann_file)

write_edges_file(df=dfAnnotation, path=owlnets_dir, ont_path=ont_dir)
write_nodes_file(df=dfAnnotation, path=owlnets_dir)
write_relations_file(path=owlnets_dir)

