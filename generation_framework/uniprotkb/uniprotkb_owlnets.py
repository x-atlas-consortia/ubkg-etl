#!/usr/bin/env python
# coding: utf-8

# Converts the TSV file downloaded (as a GZ archive) from UniProt for the UniProtKB
# ontology to OWLNETS format.

# This script is designed to align with the conversion logic executed in the build_csv.py script--e.g., outputs to
# owlnets_output, etc. This means: 1. The UNIPROTKB CSV file will be extracted from GZ and downloaded to the OWL folder
# path, even though it is not an OWL file. 2. The OWLNETS output will be stored in the OWLNETS folder path.

import argparse
import gzip
import pandas as pd
import numpy as np
import os
import glob
import logging.config
import urllib
from urllib.request import Request
import requests
import time


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


# https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(
    description='Convert the TSV file downloaded from UniProt ontology to OWLNETs .\n'
                'In general you should not have the change any of the optional arguments',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument('-l', '--owlnets_dir', type=str, default='./owlnets_output',
                    help='directory used for the owlnets output files')
parser.add_argument('-o', '--owl_dir', type=str, default='./owl',
                    help='directory used for the owl input files')
parser.add_argument('-s', '--skip_download', action='store_true',
                    help='skip downloading of the UNIPROTKB file before processing')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='increase output verbosity')
args = parser.parse_args()

# Use existing logging from build_csv.
# Note: To run this script directly as part of development or debugging
# (i.e., instead of calling it from build_csv.py), change the relative paths as follows:
# log_config = '../builds/logs'
# glob.glob('../**/logging.ini'...

log_dir, log, log_config = 'builds/logs', 'pkt_build_log.log', glob.glob('**/logging.ini', recursive=True)
logger = logging.getLogger(__name__)
logging.config.fileConfig(log_config[0], disable_existing_loggers=False, defaults={'log_file': log_dir + '/' + log})


def print_and_logger_info(message: str) -> None:
    print(message)
    logger.info(message)


if args.verbose is True:
    print('Parameters:')
    print(f' * Verbose mode')
    print(f' * Owlnets directory: {args.owlnets_dir} (exists: {os.path.isdir(args.owlnets_dir)})')
    print(f' * Owl directory: {args.owl_dir} (exists: {os.path.isdir(args.owl_dir)})')
    print(f' * Skip download of UniProtKB GZ: {args.skip_download}')

owl_sab: str = 'UNIPROTKB'
owl_dir: str = os.path.join(args.owl_dir, owl_sab)
os.system(f'mkdir -p {owl_dir}')


def download_extract_UniProtKB(zip_file: str, extract_file: str):
    # Download UNIPROTKB GZ from BioPortal.
    # The URL is a REST call that downloads a subset of the available protein information as a TSV, compressed in
    # a GZIP file. The URL can be built from the download page from the download feature.
    # The REST call downloads the following minimal information:
    # Entry
    # Entry Name
    # Protein Names
    # Gene Names
    # Reviewed (distinguishes between manually-curated Swiss proteins and automatically-annotated TREMBL proteins)

    # The query is limited to Organism = "Homo sapiens (Human)".
    request_url = 'https://rest.uniprot.org/uniprotkb/stream?compressed=true&fields=accession%2Creviewed%2Cid%2Cprotein_name%2Cgene_names%2Corganism_name%2Clength&format=tsv&query=%28%2A%29%20AND%20%28model_organism%3A9606%29'

    print_and_logger_info('Downloading UniProtKB Zip file...')

    request = Request(request_url)
    request.add_header('Accept-encoding', 'gzip')
    response = urllib.request.urlopen(request)
    with open(zip_file, 'wb') as fzip:
        while True:
            data = response.read()
            if len(data) == 0:
                break
            fzip.write(data)
    print_and_logger_info('Download complete.')

    # Extract CSV file from Zip.
    with gzip.open(zip_file, 'rb') as fzip:
        file_content = gzip.decompress(fzip.read())
    with open(extract_file, 'wt') as fout:
        fout.write(str(file_content, 'utf-8'))

    print_and_logger_info('Extracted and stored UNIPROT.TSV file.')

    return


def getAllHGNCID(hgnc_file):
    # Downloads all HGNC IDs from genenames.org.

    print_and_logger_info('Downloading HGNC ID file from genenames.org')
    url = 'http://genenames.org/cgi-bin/download/custom?col=gd_hgnc_id&col=gd_app_sym&status=Approved&hgnc_dbtag=on&order_by' \
          '=gd_app_sym_sort&format=text&submit=submit '
    response = urllib.request.urlopen(url)
    with open(hgnc_file, 'wt') as f:
        while True:
            data = str(response.read(), encoding='UTF-8')
            if len(data) == 0:
                break
            f.write(data)
    print_and_logger_info('Download of HGNC ID file complete.')

    return pd.read_csv(hgnc_file, sep='\t')


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


zip_path = os.path.join(owl_dir, 'UNIPROT.GZ')
tsv_path = os.path.join(owl_dir, 'UNIPROTKB.TSV')
hgnc_path = os.path.join(owl_dir, 'HGNC.TXT')

# ***********
if args.skip_download == True:
    print_and_logger_info('Using previously downloaded UniProtKB data.')
else:
    download_extract_UniProtKB(zip_path, tsv_path)

dfUNIPROT = pd.read_csv(tsv_path, sep='\t')
# Select only manually curated (SwissProt) proteins.
dfUNIPROT = dfUNIPROT[dfUNIPROT['Reviewed'] == 'reviewed'].dropna(subset=['Gene Names']).reset_index(drop=True)

# Get latest list of HGNC IDs from genenames.org
dfHGNC = getAllHGNCID(hgnc_path)

# Build OWLNETS text files.
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

owlnets_path: str = os.path.join(args.owlnets_dir, owl_sab)
os.system(f'mkdir -p {owlnets_path}')

edgelist_path: str = os.path.join(owlnets_path, 'OWLNETS_edgelist.txt')
#JAS 8 NOV 2022 switched predicate to use RO IRI instead of label.
predicate = 'http://purl.obolibrary.org/obo/RO_0002204'  # gene product of
print_and_logger_info('Building: ' + os.path.abspath(edgelist_path))

with open(edgelist_path, 'w') as out:
    out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')
    for index, row in dfUNIPROT.iterrows():
        subject = 'UNIPROTKB_' + row['Entry']
        # Obtain the latest HGNC ID, using the gene name.
        # Ignore synonyms or obsolete gene names.
        hgnc_name = row['Gene Names'].split(" ")[0]
        # Map to the corresponding entry in the genenames.org data.
        dfobject=dfHGNC[dfHGNC['Approved symbol'].values == hgnc_name]
        if dfobject.shape[0] > 0:
            object = 'HGNC '+ dfobject['HGNC ID'].iloc[0]
            out.write(subject + '\t' + predicate + '\t' + object + '\n')

# NODE METADATA
# Write a row for each unique concept in the 'code' column.

node_metadata_path: str = os.path.join(owlnets_path, 'OWLNETS_node_metadata.txt')
print_and_logger_info('Building: ' + os.path.abspath(node_metadata_path))

i = 1
with open(node_metadata_path, 'w') as out:
    out.write(
        'node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_definition' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')
    for index, row in dfUNIPROT.iterrows():
        node_id = 'UNIPROTKB_' + row['Entry']
        node_namespace = 'UNIPROTKB'
        node_label = row['Entry Name']
        node_definition = row['Protein names']
        node_synonyms = ''
        node_dbxrefs = ''
        out.write(
            node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

# RELATION METADATA
# Create a row for each type of relationship.

relation_path: str = os.path.join(owlnets_path, 'OWLNETS_relations.txt')
print_and_logger_info('Building: ' + os.path.abspath(relation_path))

with open(relation_path, 'w') as out:
    # header
    out.write(
        'relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\t' + 'relation_definition' + '\n')
    # The only relationship is # gene product of. The OWLNETS-UMLS-GRAPH script will find the inverse.
    out.write(predicate + '\t' + 'UNIPROTKB' + '\t' + predicate + '\t' + '' + '\n')
