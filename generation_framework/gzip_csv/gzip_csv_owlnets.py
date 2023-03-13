#!/usr/bin/env python
# coding: utf-8

# Converts to OWLNETS format the CSV file downloaded (as a GZIP archive) from BioPortal for an
# ontology to OWLNETS format.

# This script is designed to align with the conversion logic executed in the build_csv.py script--e.g., outputs to
# owlnets_output, etc. This means: 1. The CSV file will be extracted from GZ and downloaded to the OWL folder
# path, even though it is not an OWL file. 2. The OWLNETS output will be stored in the OWLNETS folder path.

# Because the CSV file will likely be small, the script will always download it. In addition,
# the script will not build a MD5 checksum.


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


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


# https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(
    description='Convert the CSV file of the ontology (of which the URL is the required parameter) ontology to OWLNETs .\n'
                'In general you should not have the change any of the optional arguments',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
# positional arguments
parser.add_argument('owl_url', type=str,
                    help='url for the CSV file to process')
parser.add_argument('owl_sab', type=str,
                    help='directory in --owlnets_dir and --owl_dir to save information from this run')
# optional arguments
parser.add_argument("-l", "--owlnets_dir", type=str, default='./owlnets_output',
                    help='directory used for the owlnets output files')
parser.add_argument("-o", "--owl_dir", type=str, default='./owl',
                    help='directory used for the owl input files')
parser.add_argument("-v", "--verbose", action="store_true",
                    help='increase output verbosity')
args = parser.parse_args()

#owl_url ="https://data.bioontology.org/ontologies/HUSAT/download?apikey=4983e1fe-1f54-412e-99bb-74764d659cb0&download_format=csv"


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

def getROproperty(sab: str, col_header: str)-> tuple[str, str]:

    # Return information on the property in Relationship Ontology (RO) that corresponds to a column
    # in a CSV file.

    # The RO property to which a CSV column header corresponds depends on the ontology.
    # For example, the "has_component" property in the Experimental Conditions Ontology (XCO),
    # corresponds to RO_0002211 (regulates); however, in PR, has_component maps to RO_002180.

    propIRI = ''
    proplbl = ''

    # Obtain the property's RO IRI with a call to the NCBO API.
    # Build the call to the NCBO API.
    # Get an API key from text file.  (The file should be excluded from github via .gitignore.)
    # (To obtain an API key, create an account with NCBO. The API key is part of the account profile.)
    fapikey = open(os.path.join(os.getcwd(),'gzip_csv/apikey.txt'),'r')
    apikey = fapikey.read()
    fapikey.close()

    #Assume simple URL encoding for the colum header.
    col_header_url = col_header.replace('_','%20')

    #Obtain property IRI from NCBO
    urlNCBO = 'https://data.bioontology.org/property_search?apikey=' + apikey + '&q=' + col_header_url + '&ontologies=' + sab + '&require_exact_match=true'
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.get(urlNCBO,headers=headers)
    if response.status_code == 200:
        responsejson = response.json()
        totalCount = responsejson.get('totalCount')
        if totalCount is not None and totalCount > 0:
            prop = responsejson.get('collection')[0]
            propIRI= prop.get('@id')

    #Obtain property label from RO.json.
    if propIRI != '':
        urlRO = 'https://raw.githubusercontent.com/oborel/obo-relations/master/ro.json'
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        response = requests.get(urlRO, headers=headers)
        if response.status_code == 200:
            responsejson = response.json()
            all_graphs = responsejson.get('graphs')
            if all_graphs is not None and len(all_graphs) > 0:
                graphs = all_graphs[0]
                nodes = graphs.get('nodes')
                for node in nodes:
                    id = node.get('id')
                    if id == propIRI:
                        proplbl = node.get('lbl')

    return (propIRI, proplbl)

if args.verbose is True:
    print('Parameters:')
    print(f" * Verbose mode")
    # if args.clean is True:
    # print(" * Cleaning owlnets directory")
    print(f" * CSV URL: {args.owl_url}")
    print(f" * CSV sab: {args.owl_sab}")
    print(f" * Owlnets directory: {args.owlnets_dir} (exists: {os.path.isdir(args.owlnets_dir)})")
    # print(f" * Owltools directory: {args.owltools_dir} (exists: {os.path.isdir(args.owltools_dir)})")
    print(f" * Owl directory: {args.owl_dir} (exists: {os.path.isdir(args.owl_dir)})")
    print('')

owl_dir: str = os.path.join(args.owl_dir, args.owl_sab)
os.system(f"mkdir -p {owl_dir}")

# Download GZip from BioPortal.
request = Request(args.owl_url)
request.add_header('Accept-encoding', 'gzip')
try:
    response = urllib.request.urlopen(request)
    zip_path = os.path.join(owl_dir, args.owl_sab + '.GZ')
except Exception as e:
    print_and_logger_info('Error downloading GZIP from BioPortal.')
    raise

with open(zip_path, 'wb') as fzip:
    while True:
        data = response.read()
        if len(data) == 0:
            break
        fzip.write(data)
print_and_logger_info(f'Downloaded ontology zip file: {zip_path}')

# Extract and read CSV file.
dfontology = pd.read_csv(zip_path,on_bad_lines='skip',encoding='utf-8')
csv_path = os.path.join(owl_dir, args.owl_sab + '.CSV')
dfontology.to_csv(csv_path)
print_and_logger_info(f'Extracted CSV to file: {csv_path}')

# Obtain the ontology-specific property that corresponds to the 'has_component' column.
has_component_tuple=getROproperty(args.owl_sab,'has_component')
print('has_component_tuple',has_component_tuple)
has_component_IRI = has_component_tuple[0]
has_component_lbl = has_component_tuple[1]

# Build OWLNETS text files.
# The OWLNETS format represents ontology data in a TSV in format:

# subject <tab> predicate <tab> object
#
# where:
#   subject - code for node in custom ontology
#   predicate - relationship
#   object: another code in the custom ontology

#  (In canonical OWLNETS, the relationship is a IRI for a relation
#  property in a standard OBO ontology, such as RO.) For custom
#  ontologies such as HuBMAP, we use custom relationship strings.)

owlnets_path: str = os.path.join(args.owlnets_dir, args.owl_sab)
os.system(f"mkdir -p {owlnets_path}")

edgelist_path: str = os.path.join(owlnets_path, 'OWLNETS_edgelist.txt')
print_and_logger_info(f'Building: {os.path.abspath(edgelist_path)}')

with open(edgelist_path, 'w') as out:
    out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')
    for index, row in dfontology.iterrows():

        if index >= 0:  # non-header
            subj = str(row['Class ID'])
            # subClassOf
            # Parents is a pipe-delimited string of IRIs.

            if str(row['Parents']) not in (np.nan, 'nan'):
                parents = row['Parents'].split('|')
                for parent in parents:
                    predicate = 'subClassOf'
                    out.write(subj + '\t' + predicate + '\t' + parent + '\n')

            # has_component
            if 'has_component' in dfontology.columns:
                if str(row['has_component']) not in (np.nan, 'nan'):
                    objIRI = str(row['has_component'])
                    obj = args.owl_sab + ' ' + objIRI[objIRI.rfind('/') + 1:len(objIRI)]
                    predicate = has_component_IRI
                    out.write(subj + '\t' + predicate + '\t' + objIRI + '\n')

# NODE METADATA
# Write a row for each unique concept in the 'code' column.

node_metadata_path: str = os.path.join(owlnets_path, 'OWLNETS_node_metadata.txt')
print_and_logger_info(f'Building: {os.path.abspath(node_metadata_path)}')

with open(node_metadata_path, 'w') as out:
    out.write(
        'node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_definition' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')
    # Root node
    #out.write(args.owl_sab + '_top' + '\t' + args.owl_sab + '\t' + 'top node' + '\t' + 'top node' + '\t' + '\t' '\n')
    for index, row in dfontology.iterrows():
        if index >= 0:  # non-header
            node = str(row['Class ID'])
            node_namespace = args.owl_sab
            node_label = str(row['Preferred Label'])
            if 'definition' in dfontology.columns:
                node_definition = str(row['definition'])
            if 'Definitions' in dfontology.columns:
                node_definition = str(row['Definitions'])

            # Note: The use case for which this was developed, XCO, has multiple synonym columns.
            # Other ontology CSVs may name synonym columns differently.
            if 'has_exact_synonyms' in dfontology.columns:
                node_synonyms = str(row['has_exact_synonym'])
            if 'Synonyms' in dfontology.columns:
                node_synonyms = str(row['Synonyms'])

            node_dbxrefs = str(row['database_cross_reference'])

            # The synonym field is an optional pipe-delimited list of string values.
            if node_synonyms in (np.nan, 'nan'):
                node_synonyms = 'None'
            # The dbxrefs field is an optional pipe-delimited list of cross-references.
            if node_dbxrefs in (np.nan, 'nan'):
                node_dbxrefs = 'None'

            node_dbxrefs = 'None'
            out.write(
                node + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

# RELATION METADATA
# Create a row for each type of relationship.

relation_path: str = os.path.join(owlnets_path, 'OWLNETS_relations.txt')
print_and_logger_info(f'Building: {os.path.abspath(relation_path)}')

with open(relation_path, 'w') as out:
    # header
    out.write(
        'relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\t' + 'relation_definition' + '\n')

    # subClassOf
    out.write('subClassOf' + '\t' + args.owl_sab + '\t' + 'subClassOf' + '\t' + '' + '\n')

    # optional has_component
    if has_component_IRI != '':
        out.write(has_component_IRI + '\t' + args.owl_sab + '\t' + has_component_lbl + '\t' + '' + '\n')
