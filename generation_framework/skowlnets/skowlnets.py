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

# ----------------------------
import argparse
import sys
import pandas as pd
import numpy as np
import os

# This script uses the codeReplacements function, which is currently in the module
# generation_framework/ubkg_utilities/parsetools.py
# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path. (This assumes that this script is being called from build_csv.py.)
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)
import ubkg_parsetools as uparse
# Extraction module
import ubkg_extract as uextract
# Logging module
import ubkg_logging as ulog
# Config file
import ubkg_config as uconfig

def download_source_file(cfg: uconfig.ubkgConfigParser, sab: str, owl_dir: str, owlnets_dir: str) -> str:

    # Obtains SimpleKnowledge source spreadsheet from Google Drive.

    # Returns the full path to the downloaded file.
    # Arguments:
    # cfg - an instance of the ubkgConfigParser class, which works with the application configuration file.
    #       The config file should contain a URL that corresponds to the SimpleKnowledge spreadsheet associated with
    #       the SAB.
    # sab - SAB for the SimpleKnowledge file--e.g., HUBMAP, SENNET, AZ
    # owl_dir - location of downloaded SimpleKnowledge files in the local repo
    # owlnets_dir - location of OWLNETS files in the local repo

    # Create output folders for source files. Use the existing OWL and OWLNETS folder structure.
    os.system(f'mkdir -p {owl_dir}')
    os.system(f'mkdir -p {owlnets_dir}')

    url = cfg.get_value(section='URL',key=sab)
    filepath = os.path.join(owl_dir,'SimpleKnowledge.xlsx')
    # Download GZIP file.
    uextract.download_file_from_google_drive(share_url=url, download_full_path=filepath)

    return filepath

def write_edges_file(df: pd.DataFrame, owlnets_dir: str):

    # Writes an edges file in OWLNETS format.
    # Arguments:
    # df - DataFrame from a SimpleKnowledge spreadsheet
    # owlnets_dir: output directory

    edgelist_path: str = os.path.join(owlnets_dir, 'OWLNETS_edgelist.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(edgelist_path))

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
                        predicate_uri = colhead

                    # Obtain codes in the proposed ontology for object concepts involved
                    # in subject-predicate-object relationships.
                    objects = row.iloc[col]

                    if not pd.isna(objects):

                        listobjects = objects.split(',')
                        for obj in listobjects:
                            if col == 4:
                                objcode = uparse.codeReplacements(obj)
                            else:
                                # Match object terms with their respective codes (Column A),
                                # which will result in a dataframe of one row.
                                match = df_sk[df_sk['term'] == obj]
                                if match.size == 0:
                                    err = 'Error: row for \'' + subject + '\' indicates relationship \'' + predicate_uri
                                    err = err + '\' with node \'' + obj + '\', but this node is not defined in the \'term\' '
                                    err = err + 'column. (Check for spelling and case of node name.)'
                                    ulog.print_and_logger_info(err)
                                    exit(1)
                                objcode = match.iloc[0, 1]

                            out.write(subject + '\t' + predicate_uri + '\t' + str(objcode) + '\n')

    return

def write_nodes_file(df: pd.DataFrame, owlnets_dir: str):

    # Writes a nodes file in OWLNETS format.
    # Arguments:
    # df - DataFrame from a SimpleKnowledge spreadsheet
    # owlnets_dir: output directory

    # NODE METADATA
    # Write a row for each unique concept in the 'code' column.

    node_metadata_path: str = os.path.join(owlnets_dir, 'OWLNETS_node_metadata.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(node_metadata_path))

    with open(node_metadata_path, 'w') as out:
        out.write(
            'node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_definition' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')

        for index, row in df_sk.iterrows():
            if index >= 0:  # non-header
                node_id = str(row['code'])
                node_namespace = ''
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

    return

def write_relations_file(df: pd.DataFrame, owlnets_dir: str):

    # Writes a relations file in OWLNETS format.
    # Arguments:
    # df - DataFrame from a SimpleKnowledge spreadsheet
    # owlnets_dir: output directory

    # RELATION METADATA
    # Create a row for each type of relationship.

    relation_path: str = os.path.join(owlnets_dir, 'OWLNETS_relations.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(relation_path))

    with open(relation_path, 'w') as out:
        # header
        out.write(
            'relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\t' + 'relation_definition' + '\n')

        # The first relationship is a subClassOf, which the OWLNETS-UMLS-GRAPH script will convert to an isa.
        out.write('subClassOf' + '\t' + '' + '\t' + 'subClassOf' + '\t' + '' + '\n')

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

    return

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

def getargs()->argparse.Namespace:
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description='Builds ontology files in OWLNETS format from a spreadsheet in SimpleKnowledge format.',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("sab", help="Name of SimpleKnowledge ontology")
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")
    args = parser.parse_args()

    return args

# -----------------------------------------
# START

args = getargs()

# Read from config file.
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/skowlnets/skowlnets.ini')
skowlnets_config = uconfig.ubkgConfigParser(cfgfile)

# Get OWL and OWLNETS directories.
# The config file contains absolute paths to the parent directories in the local repo.
# Affix the SAB to the paths.
owl_dir = os.path.join(os.path.dirname(os.getcwd()),skowlnets_config.get_value(section='Directories',key='owl_dir'),args.sab)
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()),skowlnets_config.get_value(section='Directories',key='owlnets_dir'),args.sab)

if args.skipbuild:
    sk_file = os.path.join(owl_dir,'SimpleKnowledge.xlsx')
else:
    # Download the SimpleKnowledge spreadsheet.
    sk_file=download_source_file(cfg=skowlnets_config,sab=args.sab,owl_dir=owl_dir,owlnets_dir=owlnets_dir)

# Load SimpleKnowledge spreadsheet into a DataFrame.
df_sk = pd.read_excel(sk_file)

# Generate the OWLNETS files.
write_edges_file(df=df_sk,owlnets_dir=owlnets_dir)
write_nodes_file(df=df_sk,owlnets_dir=owlnets_dir)
write_relations_file(df=df_sk,owlnets_dir=owlnets_dir)
