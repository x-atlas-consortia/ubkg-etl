#!/usr/bin/env python
# coding: utf-8

# Converts to OWLNETS format the CSV file downloaded (as a GZIP archive) from BioPortal for an
# ontology to OWLNETS format.

# This script is designed to align with the conversion logic executed in the build_csv.py script--e.g., outputs to
# owlnets_output, etc. This means: 1. The CSV file will be extracted from GZ and downloaded to the OWL folder
# path, even though it is not an OWL file. 2. The OWLNETS output will be stored in the OWLNETS folder path.

import argparse
import pandas as pd
import numpy as np
import os
import sys
import urllib
from urllib.request import Request
import requests

# Import UBKG utilities which is in a directory that is at the same level as the script directory.
# Go "up and over" for an absolute path.
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath,'generation_framework/ubkg_utilities')
sys.path.append(fpath)
# Extraction module
import ubkg_extract as uextract
# Logging module
import ubkg_logging as ulog
# Parser
import ubkg_parsetools as uparse

def getAPIKey()->str:

    # Get an API key from a text file in the application directory.  (The file should be excluded from github via .gitignore.)
    # (To obtain an API key, create an account with NCBO. The API key is part of the account profile.)
    try:
        fapikey = open(os.path.join(os.getcwd(), 'gzip_csv/apikey.txt'), 'r')
        apikey = fapikey.read()
        fapikey.close()
    except FileNotFoundError as e:
        ulog.print_and_logger_info('Missing file: apikey.txt')
        exit(1)

    return apikey

def translate_SAB_Property_label_to_RO_IRI(apikey: str, sab: str, label: str)-> tuple[str,str]:

    # Translates the label for a property from a SAB into the corresponding property from the Relations Ontology (RO).
    # Returns a tuple of (IRI, label) from RO.

    # Arguments:
    # apikey: API key used to call the NCBO REST API
    # sab: ontology for which the label argument corresponds to a property
    # label: label for a property in the ontology referenced by the SAB

    # Example returns:
    # sab=XCO label=has_component translates to RO_0002211 (regulates)
    # sab=PR label=has_component translates to RO_0002180 (has_component)

    propIRI = ''
    proplbl = ''

    # Assume simple URL encoding for the colum header.
    label = label.replace('_', '%20')

    # Obtain from NCBO API the property IRI corresponding to sab:label.
    urlNCBO = 'https://data.bioontology.org/property_search?apikey=' + apikey + '&q=' + label + '&ontologies=' + sab + '&require_exact_match=true'
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.get(urlNCBO, headers=headers)
    if response.status_code == 200:
        responsejson = response.json()
        totalCount = responsejson.get('totalCount')
        if totalCount is not None and totalCount > 0:
            prop = responsejson.get('collection')[0]
            propIRI = prop.get('@id')

    # Obtain corresponding property label from RO.json.
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

    ulog.print_and_logger_info(f'In {sab}, the has_component property translates to {propIRI} ({proplbl}).')
    return (propIRI, proplbl)

def getROproperty(sab: str, col_header: str)-> tuple[str, str]:

    # Return information on the property in Relationship Ontology (RO) that corresponds to a column
    # in a CSV file. The column header corresponds to the label of a relationship property in the ontology
    # represented by the CSV.

    # In general, two ontologies with the same labeled property may correspond to different RO properties.

    # For example, the "has_component" property in the Experimental Conditions Ontology (XCO)
    # corresponds to RO_0002211 (regulates); however, in PR, has_component maps to RO_002180.

    # Arguments:
    # sab - identifier for the ontology in NCBO
    # col_header - string that corresponds to a column header in a NCBO OWL CSV file.

    # Obtain the property's RO IRI with a call to the NCBO API.
    # Obtain an api key for the NCBO API.
    apikey = getAPIKey()
    # Translate to an RO property.
    return translate_SAB_Property_label_to_RO_IRI(apikey=apikey,sab=sab,label=col_header)

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

def getargs()->argparse.Namespace:

    # Parse command line arguments.
    parser = argparse.ArgumentParser(
    description='Convert the CSV file of the ontology (of which the URL is the required parameter) ontology to OWLNETs .\n'
                'In general you should not have the change any of the optional arguments.',
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
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")
    args = parser.parse_args()

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
    return args

def write_edges_file(df:pd.DataFrame, owlnets_dir: str, has_component_IRI: str,sab:str):

    # Writes an edges file in OWLNETS format.
    # Arguments:
    # df - DataFrame of source data
    # owlnets_dir - output directory
    # has_component_IRI - IRI for the 'has_component' relationship
    # sab: SAB for ontology

    # Assumptions about the CSV file that is the source of the DataFrame:
    # 1. The identifiers in the following columns are IRIs that are compliant with OBO principle 3
    #     --e.g.,http://purl.obolibrary.org/obo/XCO_0000121
    #    a. Class ID
    #    b. Parents
    #    c. has_component
    # 2. The IRIs in the Parents column are pipe-delimited

    # The OWLNETS format represents ontology data in a TSV in format:

    # subject <tab> predicate <tab> object
    #
    # where:
    #   subject - code for node in custom ontology
    #   predicate - a single relationship other than subClassOf--e.g., 'has_component'
    #   object: another code in the custom ontology

    #  (In canonical OWLNETS, the relationship is a IRI for a relation
    #  property in a standard OBO ontology, such as RO.) For custom
    #  ontologies such as HuBMAP, we use custom relationship strings.)

    edgelist_path: str = os.path.join(owlnets_dir, 'OWLNETS_edgelist.txt')
    ulog.print_and_logger_info(f'Building: {os.path.abspath(edgelist_path)}')

    # Convert the Class ID to a standard node ID for the subject.
    df['subject'] = uparse.codeReplacements(df['Class ID'],sab)

    with open(edgelist_path, 'w') as out:
        out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')
        for index, row in df.iterrows():

            if index >= 0:  # non-header
                #subj = str(row['Class ID'])
                subj = str(row['subject'])

                # subClassOf
                # Parents is a pipe-delimited string of IRIs.
                if str(row['Parents']) not in (np.nan, 'nan'):
                    parents = row['Parents'].split('|')
                    for parent in parents:
                        # Parse node ID. Assume OBO 3 IRI.
                        obj = parent.replace(':', ' ').replace('#', ' ').replace('_', ' ').split('/')[-1]
                        predicate = 'subClassOf'
                        if parent !='':
                            out.write(subj + '\t' + predicate + '\t' + obj + '\n')

                # has_component
                predicate = has_component_IRI
                if 'has_component' in dfontology.columns:
                    if str(row['has_component']) not in (np.nan, 'nan'):
                        objIRI = str(row['has_component'])
                        #obj = args.owl_sab + ' ' + objIRI[objIRI.rfind('/') + 1:len(objIRI)]
                        #Parse node ID. Assume OBO 3 IRI.
                        obj = objIRI.replace(':', ' ').replace('#', ' ').replace('_', ' ').split('/')[-1]
                        out.write(subj + '\t' + predicate + '\t' + obj + '\n')
    return

def write_nodes_file(df:pd.DataFrame, owlnets_dir: str):

    # Writes a nodes file in OWLNETS format.
    # Arguments:
    # df - DataFrame of source information
    # owlnets_dir: output directory

    # NODE METADATA
    # Write a row for each unique concept in the 'code' column.

    node_metadata_path: str = os.path.join(owlnets_dir, 'OWLNETS_node_metadata.txt')
    ulog.print_and_logger_info(f'Building: {os.path.abspath(node_metadata_path)}')

    with open(node_metadata_path, 'w') as out:
        out.write(
            'node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_definition' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')
        # Root node
        # out.write(args.owl_sab + '_top' + '\t' + args.owl_sab + '\t' + 'top node' + '\t' + 'top node' + '\t' + '\t' '\n')
        for index, row in df.iterrows():
            if index >= 0:  # non-header
                node = str(row['Class ID'])
                node_namespace = args.owl_sab
                node_label = str(row['Preferred Label'])

                if 'definition' in df.columns:
                    node_definition = str(row['definition'])
                if 'Definitions' in df.columns:
                    node_definition = str(row['Definitions'])

                # Note: The use case for which this was developed, XCO, has multiple synonym columns.
                # Other ontology CSVs may name synonym columns differently.
                if 'has_exact_synonyms' in df.columns:
                    node_synonyms = str(row['has_exact_synonym'])
                if 'Synonyms' in df.columns:
                    node_synonyms = str(row['Synonyms'])

                # June 2023 - HRAVS uses a different column name for database_cross_reference.
                # It's unclear whether the CSV format is standard--i.e., that there should be a column named
                # database_cross_reference.
                if 'database_cross_reference' in df.columns:
                    node_dbxrefs = str(row['database_cross_reference'])
                elif 'http://www.geneontology.org/formats/oboInOwl#hasDbXref' in df.columns:
                    node_dbxrefs = str(row['http://www.geneontology.org/formats/oboInOwl#hasDbXref'])
                else:
                    node_dbxrefs = np.nan

                # The synonym field is an optional pipe-delimited list of string values.
                if node_synonyms in (np.nan, 'nan'):
                    node_synonyms = 'None'
                # The dbxrefs field is an optional pipe-delimited list of cross-references.
                if node_dbxrefs in (np.nan, 'nan'):
                    node_dbxrefs = 'None'

                out.write(
                    node + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')
    return

def write_relations_file(owlnets_dir: str, predicate:str, label:str):

    # Writes a relations file in OWLNETS format.
    # Arguments:
    # owlnets_dir: output directory
    # predicate: the single relationship predicate
    # label: label for the predicate

    # RELATION METADATA
    # Create a row for each type of relationship.

    relation_path: str = os.path.join(owlnets_dir, 'OWLNETS_relations.txt')
    ulog.print_and_logger_info(f'Building: {os.path.abspath(relation_path)}')

    with open(relation_path, 'w') as out:
        # header
        out.write(
            'relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\t' + 'relation_definition' + '\n')

        # subClassOf
        out.write('subClassOf' + '\t' + args.owl_sab + '\t' + 'subClassOf' + '\t' + '' + '\n')

        # optional has_component
        if has_component_IRI != '':
            out.write(predicate + '\t' + args.owl_sab + '\t' + has_component_lbl + '\t' + '' + '\n')

    return

def getdfCSV(owl_dir: str, csv_file: str) -> pd.DataFrame:

    # Read and prepare CSV file.

    # Arguments:
    # owl_dir: path to the OWL files for the ontology
    # csv_file: file name of the CSV

    csv_path = os.path.join(owl_dir, csv_file)
    ulog.print_and_logger_info(f'Reading {csv_path}...')
    dfontology = uextract.read_csv_with_progress_bar(csv_path, on_bad_lines='skip', encoding='utf-8', sep=',')
    dfontology = dfontology.replace({'None': np.nan})
    dfontology = dfontology.replace({'': np.nan})
    # JAS OCT 2023 Change to add all nodes to allow for nodes without parents.
    # Use case: HRAVS, which as of Oct 2023 was the only use case for this script.
    # Drop rows without at least subclass relationships.
    # dfontology = dfontology.dropna(subset=['Class ID', 'Parents'])

    return dfontology

#--------------------------
# MAIN

# Parse arguments.
args = getargs()
print(args.owl_sab)

# Set file paths.
owl_dir = os.path.join(args.owl_dir, args.owl_sab)
owlnets_dir = os.path.join(args.owlnets_dir, args.owl_sab)

# Set file names for downloads.
zip_filename = args.owl_sab + '.GZ'
csv_filename = args.owl_sab + '.CSV'

# Download GZipped file and extract the CSV.
if not args.skipbuild:
    uextract.get_gzipped_file(gzip_url=args.owl_url, zip_path=owl_dir, extract_path=owl_dir, zipfilename=zip_filename,outfilename=csv_filename)

# Load the CSV file.
dfontology = getdfCSV(owl_dir=owl_dir,csv_file=csv_filename)

# Obtain the ontology-specific property that corresponds to the 'has_component' column.
has_component_tuple=getROproperty(args.owl_sab,'has_component')
has_component_IRI = has_component_tuple[0]
has_component_lbl = has_component_tuple[1]

if has_component_IRI == '':
    # Use default from RO.
    has_component_IRI = 'RO_002180'
    has_component_lbl = 'has_component'

# Build OWLNETS text files.
write_edges_file(df=dfontology,owlnets_dir=owlnets_dir,has_component_IRI=has_component_IRI,sab=args.owl_sab)
write_nodes_file(df=dfontology,owlnets_dir=owlnets_dir)
write_relations_file(owlnets_dir=owlnets_dir,predicate=has_component_IRI,label=has_component_lbl)

