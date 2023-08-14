#!/usr/bin/env python
# coding: utf-8

# Converts the TSV file downloaded (as a GZ archive) from UniProt for the UniProtKB
# ontology to OWLNETS format.

# This script is designed to align with the conversion logic executed in the build_csv.py script--e.g., outputs to
# owlnets_output, etc. This means: 1. The UNIPROTKB CSV file will be extracted from GZ and downloaded to the OWL folder
# path, even though it is not an OWL file. 2. The OWLNETS output will be stored in the OWLNETS folder path.

import sys
import pandas as pd
import numpy as np
import os
import requests
import argparse
import re
from tqdm import tqdm

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


def getUNIPROTKB(cfg: uconfig.ubkgConfigParser, owl_dir: str, owlnets_dir: str) -> pd.DataFrame:

    # Executes queries in the UNIPROTKB API that downloads GZip files of UNIPROTKB data.
    # Extracts the contents of the GZips--which should be TSVs.
    # Loads the contents into a DataFrame.
    # Consolidates DataFrames into a single TSV if more than one organism was specified in the query.

    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    # owl_dir: directory to which to download the GZIP file.
    # owlnets_dir: directory to which to extract the contents of the GZIP--a TSV file.

    # Results:
    # 1. A file named UNIPROTKB_x.tsv for every organism x identified in the configuration file.
    # 2. A file named UNIPROTKB_ALL.tsv that consolidates all organism data. This file will be created even if there
    #    is only one organism specified in the configuration file.

    # Query URL
    base_url = cfg.get_value(section='URL', key='BaseQuery')

    # Determine whether to filter to only reviewed (SwissProt).
    reviewed = cfg.get_value(section='Filters', key='reviewed')
    rev = ''
    msgreviewed = ' - both manually curated (SwissProt) and automatically curated (TrEMBL)'
    if reviewed == 'True':
        rev = 'AND%20%28reviewed%3Atrue%29'
        msgreviewed = ' - manually curated (SwissProt) only'

    # Query for each organism in the list.
    list_org = []
    for org in cfg.config['Organisms']:
        # Determine the organism for which to download UNIPROTKB data.
        organism = cfg.get_value(section='Organisms', key=org)
        ulog.print_and_logger_info(f'Downloading for organism: {org} {msgreviewed}')

        # Download GZip file and extract the TSV file from it.
        zipfilename = f'UNIPROTKB_{org}.gz'
        tsvfilename = f'UNIPROTKB_{org}.tsv'

        url = base_url+organism+rev
        uextract.get_gzipped_file(gzip_url=url, zip_path=owl_dir, extract_path=owlnets_dir, zipfilename=zipfilename,
                                  outfilename=tsvfilename)

        # Load the extracted TSV file into a DataFrame.
        tsvpath = os.path.join(owlnets_dir, tsvfilename)
        list_org.append(uextract.read_csv_with_progress_bar(path=tsvpath, sep='\t', on_bad_lines='skip'))

        # Select only manually curated (SwissProt) proteins.
        # df = df[df['Reviewed'] == 'reviewed'].dropna(subset=['Gene Names']).reset_index(drop=True)

    # Concatenate DataFrames for all organisms.
    df = pd.concat(list_org, axis=0, ignore_index=True)
    df = df.fillna('')

    ulog.print_and_logger_info('Writing consolidated TSV UNIPROTKB_all.tsv')
    path_consolidated = os.path.join(owlnets_dir, 'UNIPROTKB_all.tsv')
    uextract.to_csv_with_progress_bar(df=df, path=path_consolidated, sep='\t')
    return df


def getAllHGNCID(cfg: uconfig.ubkgConfigParser, owl_dir: str) -> pd.DataFrame:
    # Downloads all HGNC IDs from genenames.org.

    # Returns a DataFrame of the HGNC information.

    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    # owl_dir: directory to which to download the GZIP file.

    ulog.print_and_logger_info('Downloading HGNC ID file from genenames.org')
    # Obtain the URL from the configuration file.
    url = cfg.get_value(section='HGNC', key='URL')

    hgnc_path = os.path.join(owl_dir, 'HGNC.TSV')
    uextract.download_file(url=url, download_full_path=hgnc_path)

    return uextract.read_csv_with_progress_bar(path=hgnc_path, sep='\t')


def getHGNCID(HGNCacronym: str):
    # Queries the HGNC REST API to obtain the HGNC ID, given an acronym.
    # This is slow: the getAllHGNCID function is the preferred method.

    hgnc = ''
    urlHGNC = 'http://rest.genenames.org/search/symbol/' + HGNCacronym
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.get(urlHGNC, headers=headers)
    if response.status_code == 200:
        numfound = response.json().get('response').get('numFound')
        if numfound >= 0:
            docs = response.json().get('response').get('docs')
            if len(docs) > 0:
                hgnc = docs[0].get('hgnc_id')
    return hgnc


def write_edges_file(df: pd.DataFrame, dfHGNC: pd.DataFrame, owlnets_dir: str, predicate: str):

    # Writes an edges file in OWLNETS format.
    # Arguments:
    # df - DataFrame of UNIPROTKB data
    # owlnets_dir: output directory
    # dfHGNC: a DataFrame of HGNC data

    # The OWLNETS format represents ontology data in a TSV in format:

    # subject <tab> predicate <tab> object
    #
    # where:
    #   subject - code for node in custom ontology
    #   predicate - relationship
    #   object: another code in the custom ontology

    #  (In canonical OWLNETS, the relationship is a URI for a relation
    #  property in a standard OBO ontology, such as RO.) For custom
    #  ontologies such as HuBMAP, we use custom relationship strings.)

    edgelist_path: str = os.path.join(owlnets_dir, 'OWLNETS_edgelist.txt')

    ulog.print_and_logger_info('Building: ' + os.path.abspath(edgelist_path))

    with open(edgelist_path, 'w') as out:
        out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')
        # Show TQDM progress bar.
        for index, row in tqdm(df.iterrows(), total=df.shape[0]):
            subject = 'UNIPROTKB:' + row['Entry']
            # Obtain the latest HGNC ID, using the gene name.
            # Ignore synonyms or obsolete gene names.
            hgnc_name = row['Gene Names'].split(' ')[0]
            # Map to the corresponding entry in the genenames.org data.
            dfobject = dfHGNC[dfHGNC['Approved symbol'].values == hgnc_name]
            # JULY 2023 - CodeID format changed to SAB:CODE.
            if dfobject.shape[0] > 0:
                #object = 'HGNC ' + dfobject['HGNC ID'].iloc[0]
                object = dfobject['HGNC ID'].iloc[0]
                out.write(subject + '\t' + predicate + '\t' + object + '\n')

    return


def write_nodes_file(df: pd.DataFrame,  owlnets_dir: str):

    # Writes a nodes file in OWLNETS format.
    # Arguments:
    # df - DataFrame of source information
    # owlnets_dir: output directory

    # NODE METADATA
    # Write a row for each unique concept in the 'code' column.

    # Only UNIPROTKB codes need to be in the nodes file.
    # HGNC IDs are part of the UMLS data.

    node_metadata_path: str = os.path.join(owlnets_dir, 'OWLNETS_node_metadata.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(node_metadata_path))

    with open(node_metadata_path, 'w') as out:
        out.write(
            'node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_definition' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')
        # Show TQDM progress bar.
        for index, row in tqdm(df.iterrows(), total=df.shape[0]):
            node_id = 'UNIPROTKB:' + row['Entry']
            node_namespace = 'UNIPROTKB'
            # August 2023
            # The Protein Names field delimits using parenthesis--e.g., Approved name (synonym 1) (synonym 2)
            # Set the preferred term to be the first entry in the Protein Names field from UniProtKB.
            # Set all other names to be synonyms.
            # node_label = row['Entry Name']
            # node_definition = row['Protein names']

            # Split on the pair of parentheses.
            protein_names = row['Protein names']
            protein_names = re.split(r'[()]', protein_names)
            # Remove extraneous blanks.
            for n in protein_names:
                if n.strip() == '':
                    protein_names.remove(n)

            # The recommended name is the first in the list.
            node_label = protein_names[0]

            # Synonyms:
            # Replace the approved name with the UniProtKB Entry Name, so it will the first synonym.
            protein_names[0]=row['Entry Name']
            # Delimit.
            node_synonyms = '|'.join(protein_names)

            node_definition = row['Function [CC]']

            node_dbxrefs = ''

            out.write(
                node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

    return


def write_relations_file(owlnets_dir: str, predicate:str):

    # Writes a relations file in OWLNETS format.
    # Arguments:
    # df - DataFrame of source information
    # owlnets_dir: output directory
    # predicate: the single relationship predicate

    # RELATION METADATA
    # Create a row for each type of relationship.

    relation_path: str = os.path.join(owlnets_dir, 'OWLNETS_relations.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(relation_path))

    with open(relation_path, 'w') as out:
        # header
        out.write(
            'relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\t' + 'relation_definition' + '\n')
        out.write(predicate + '\t' + 'UNIPROTKB' + '\t' + predicate + '\t' + '' + '\n')
    return


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


def getargs()->argparse.Namespace:
    # Parse command line arguments.
    parser = argparse.ArgumentParser(
        description='Builds OWLNETS files from UNIPROTKB source',
        formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")

    return parser.parse_args()


# -----------------------------------------------------
# START

args = getargs()

# Read from config file
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/uniprotkb/uniprotkb.ini')
config = uconfig.ubkgConfigParser(cfgfile)

# Get OWL and OWLNETS directories.
# The config file should contain absolute paths to the directories.
owl_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owl_dir'))
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owlnets_dir'))

# Get UNIPROTKB and HGNC source files.
if args.skipbuild:
    # Read previously downloaded file.
    filepath = os.path.join(os.path.join(owlnets_dir, 'UNIPROTKB_all.tsv'))
    dfUNIPROT = uextract.read_csv_with_progress_bar(filepath, sep='\t')
    dfUNIPROT = dfUNIPROT.replace(np.nan, '', regex=True)

    # Read previously downloaded HGNC information.
    hgncpath = os.path.join(owl_dir, 'HGNC.TSV')
    dfHGNC = uextract.read_csv_with_progress_bar(hgncpath, sep='\t')
    dfHGNC = dfHGNC.replace(np.nan, '', regex=True)
else:
    # Download file from UNIPROTKB.
    dfUNIPROT = getUNIPROTKB(cfg=config, owl_dir=owl_dir, owlnets_dir=owlnets_dir)
    # Get latest list of HGNC IDs from genenames.org
    dfHGNC = getAllHGNCID(cfg=config, owl_dir=owl_dir)

# Build OWLNETS text files.
# Generate the OWLNETS files.
# Only one predicate from the Relations Ontology is used.
# The OWLNETS-UMLS-GRAPH script will find the inverse.
predicate = 'http://purl.obolibrary.org/obo/RO_0002204'  # gene product of

write_edges_file(df=dfUNIPROT, dfHGNC=dfHGNC, owlnets_dir=owlnets_dir, predicate=predicate)
write_nodes_file(df=dfUNIPROT, owlnets_dir=owlnets_dir)
write_relations_file(owlnets_dir=owlnets_dir, predicate=predicate)
