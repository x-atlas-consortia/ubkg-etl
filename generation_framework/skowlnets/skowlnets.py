#!/usr/bin/env python
# coding: utf-8

# # SimpleKnowledge to OWLNETS converter
# 
# Uses the input spreadsheet for the SimpleKnowledge Editor to generate a set of text files that comply with the
# OWLNETS format, as described in https://github.com/callahantiff/PheKnowLator/blob/master/notebooks
# /OWLNETS_Example_Application.ipynb.
# 
# User guide to build the SimpleKnowledge Editor spreadsheet:
# https://docs.google.com/document/d/1wjsOzJYRV2FRehX7NQI74ZKRXvH45l0QmClBBF_VypM/edit?usp=sharing

# SimpleKnowledge to OWLNETS converter

# Uses the input spreadsheet for the SimpleKnowledge Editor to generate text files that comply with the OWLNETS format.

# This script is designed to align with the PheKnowLator logic executed in the build_csv.py script--e.g., outputs
# to owlnets_output, etc.

import argparse
import sys
import pandas as pd
import numpy as np
import os
import glob
import logging.config

# JAS FEB 2023
# This script uses the codeReplacements function, which is currently in the module
# scripts/ubkg_utilities/parsetools.py
# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path. (This assumes that this script is being called from build_csv.py.)
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath,'scripts/ubkg_utilities')
sys.path.append(fpath)
import parsetools

# Parse an argument that identifies the version of the UMLS in Neptune from which to build
# the CSV files.
class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


parser = argparse.ArgumentParser(
    description='Builds ontology files in OWLNETS format from a spreadsheet in SimpleKnowledge format.',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument("skfile", help="SimpleKnowledge spreadsheet name")
parser.add_argument("sab", help="Name of SimpleKnowledge ontology")
# JAS FEB 2023 Moved the expected location of the SimpleKnowledge file to a subdirectory in the OWL path.
parser.add_argument("-s", "--sk_dir", type=str, default='./owl',
                    help="parent directory of the directory that contains the SimpleKnowledge spreadsheet")
parser.add_argument("-l", "--owlnets_dir", type=str, default="./owlnets_output",
                    help="directory containing the owlnets output directories")
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

# JAS FEB 2023 Moved the expected location of the SimpleKnowledge file from the inport director to a subdirectory
# of the OWL folder.
# Read input spreadsheet.
input_path: str = os.path.join(args.sk_dir, args.sab, args.skfile)
try:
    df_sk = pd.read_excel(input_path, sheet_name='SimpleKnowledgeEditor')
except FileNotFoundError:
    err = 'Missing input spreadsheet: ' + os.path.abspath(input_path)
    raise SystemExit(err)

# Build OWLNETS text files.
# The OWLNETS format represents ontology data in a TSV in format:

# subject <tab> predicate <tab> object
#
# where:
#   subject - code for node in custom ontology
#   predicate - relationship
#   object: another code in the custom ontology
#
#  (In canonical OWLNETS, the relationship is a URI for a relation 
#  property in a standard OBO ontology, such as RO.) For custom
#  ontologies such as HuBMAP, we use custom relationship strings.)
owlnets_path: str = os.path.join(args.owlnets_dir, args.sab)
os.system(f"mkdir -p {owlnets_path}")

edgelist_path: str = os.path.join(owlnets_path, 'OWLNETS_edgelist.txt')
print_and_logger_info('Building: ' + os.path.abspath(edgelist_path))

with open(edgelist_path, 'w') as out:
    out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')

    # Each column after E in the spreadsheet (isa, etc.) represents a type of
    # subject-predicate_object relationship.
    #   1. Column E represents the dbxrefs. The dbxrefs field is an optional list of references to
    #      concept IDs in other vocabularies, delimited
    #      with a comma between SAB and ID and a pipe between entries--e.g,
    #      SNOMEDCT_US:999999,UMLS:C99999. This list should be exploded and then subClassOf relationship rows
    #      written.
    #   2. Column F represents the isa relationship. This corresponds to a isa relationship within the
    #      custom ontology.
    #   3. Columns after F represent relationships other than isa in the custom ontology.

    # Cells in relationship columns contain comma-separated lists of object nodes.

    # Thus, a relationship cell, in general, represents a set of subject-predicate-object
    # relationships between the concept in the "code" cell and the concepts in the relationship
    # cell.

    for index, row in df_sk.iterrows():

        if index >= 0:  # non-header
            subject = str(row['code'])

            # JAS 8 NOV 2022: Changed start of range from 4 to 5 the "dbxref" column.
            # dbxref is not a custom relationship, but an equivalence class.
            for col in range(5, len(row)):
                # Obtain relationship (predicate)
                if col == 5:
                    # The OWLNETS-UMLS-GRAPH script converts subClassOf into isa and inverse_isa relationships.
                    predicate_uri = "subClassOf"

                else:
                    # custom relationship (predicate)
                    colhead = df_sk.columns[col]
                    # predicate_uri = colhead[colhead.find('(')+1:colhead.find(')')]
                    predicate_uri = colhead

                # Obtain codes in the proposed ontology for object concepts involved
                # in subject-predicate-object relationships.
                objects = row.iloc[col]

                if not pd.isna(objects):

                    listobjects = objects.split(',')
                    for obj in listobjects:
                        if col == 4:
                            objcode = parsetools.codeReplacements(obj)
                        else:
                            # Match object terms with their respective codes (Column A),
                            # which will result in a dataframe of one row.
                            match = df_sk[df_sk['term'] == obj]
                            if match.size == 0:
                                err = 'Error: row for \'' + subject + '\' indicates relationship \'' + predicate_uri
                                err = err + '\' with node \'' + obj + '\', but this node is not defined in the \'term\' '
                                err = err + 'column. (Check for spelling and case of node name.)'
                                print_and_logger_info(err)
                            objcode = match.iloc[0, 1]

                        out.write(subject + '\t' + predicate_uri + '\t' + str(objcode) + '\n')

# NODE METADATA
# Write a row for each unique concept in the 'code' column.

node_metadata_path: str = os.path.join(owlnets_path, 'OWLNETS_node_metadata.txt')
print_and_logger_info('Building: ' + os.path.abspath(node_metadata_path))

with open(node_metadata_path, 'w') as out:
    out.write(
        'node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_definition' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')

    for index, row in df_sk.iterrows():
        if index >= 0:  # non-header
            node_id = str(row['code'])
            node_namespace = 'HUBMAP'
            node_label = str(row['term'])
            node_definition = str(row['definition'])

            node_synonyms = str(row['synonyms'])
            # The synonym field is an optional pipe-delimited list of string values.
            if node_synonyms in (np.nan, 'nan'):
                node_synonyms = ''

            node_dbxrefs = str(row['dbxrefs'])
            if node_dbxrefs in (np.nan, 'nan'):
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

    # The first relationship is a subClassOf, which the OWLNETS-UMLS-GRAPH script will convert to an isa.
    out.write('subClassOf' + '\t' + 'HUBMAP' + '\t' + 'subClassOf' + '\t' + '' + '\n')

    # The values from the dbxref column correspond to a pipe-delimited, colon-delimited set
    # of concepts in other vocabularies in the onotology. These will be expanded to a set of
    # subClassOf relationships to establish the polyhierarchy.

    # Establish the remaining custom relationships.
    for col in range(6, len(df_sk.columns)):
        colhead = df_sk.columns[col]

        if colhead != 'dbxrefs':
            # predicate_uri = colhead[colhead.find('(')+1:colhead.find(')')]
            predicate_uri = colhead
            relation_namespace = args.sab
            relation_definition = ''
            # out.write(predicate_uri + '\t' + relation_namespace + '\t' + label + '\t' + relation_definition + '\n')
            out.write(
                predicate_uri + '\t' + relation_namespace + '\t' + predicate_uri + '\t' + relation_definition + '\n')
