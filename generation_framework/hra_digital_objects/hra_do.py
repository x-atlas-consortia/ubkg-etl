#!/usr/bin/env python
# coding: utf-8

# Human Reference Atlas Digital Object cell annotation crosswalk CSV to OWLNETS converter
# 
# Uses a crosswalk spreadsheet available in the Human Reference Atlast to generate a set of
# text files that comply with the
# OWLNETS format, as described in https://github.com/callahantiff/PheKnowLator/blob/master/notebooks
# /OWLNETS_Example_Application.ipynb.
#

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
from urllib.parse import urlparse

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

    """
    Obtains a cell annotation crosswalk spreadsheet from the Human Reference Atlas's Digital Objects site.

    :param cfg: an instance of the ubkgConfigParser class, which works with the application configuration file.
                The config file should contain a URL that corresponds to the SimpleKnowledge spreadsheet
                associated with the SAB.
    :param sab: SAB for the annotation file--e.g., AZ, PAZ
    :param owl_dir: location of downloaded crosswalk files in the local repo
    :param owlnets_dir: location of OWLNETS files in the local repo

    :returns: the full path to the downloaded file

    """

    # Create output folders for source files. Use the existing OWL and OWLNETS folder structure.
    os.system(f'mkdir -p {owl_dir}')
    os.system(f'mkdir -p {owlnets_dir}')

    url = cfg.get_value(section='URL',key=sab)
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    filepath = os.path.join(owl_dir,filename)
    uextract.download_file(url=url, download_full_path=filepath)

    return filepath

def encode_organ_level_nodes(df: pd.DataFrame, parents: dict, sab:str) -> pd.DataFrame:
    """
    Encodes organ level nodes relative to the organ level parent.
    :param df: DataFrame from a HRA cell type annotation CSV.
    :param parents: dict of parent nodes
    :param sab: sab for annotation
    :return: DataFrame of just organ level node codes and terms
    """
    dforgan = df.drop_duplicates(subset=['Organ_Level']).copy()
    organ_level_parent_code = int(parents['organ_level_parent_node']['code'].split(':')[1])
    start_code = organ_level_parent_code + 1
    dforgan['Organ_AZ_code'] = [
        f"{sab}:{code}"
        for code in range(start_code, start_code + len(dforgan))]

    return dforgan[['Organ_Level','Organ_ID','Organ_AZ_code']]

def write_edges_file(df: pd.DataFrame, parents: dict, dforgan: pd.DataFrame, owlnets_dir: str, sab:str):

    """
    Writes an edge file in OWLNETS format.

    :param df: DataFrame from a HRA cell type annotation CSV.
    :param owlnets_dir: output directory
    :param parents: dict of parent nodes
    :param dforgan: DataFrame of organ level node information
    :param sab: sab for annotation
    """

    edgelist_path: str = os.path.join(owlnets_dir, 'OWLNETS_edgelist.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(edgelist_path))

    with open(edgelist_path, 'w') as out:
        out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')

        # isa relationships
        # organ level to parent
        predicate_uri = 'isa'

        objcode = parents['parent_node']['code']

        subject = parents['organ_level_parent_node']['code']
        out.write(subject + '\t' + predicate_uri + '\t' + str(objcode) + '\n')

        # cell type annotation to parent
        subject = parents['cell_annotation_parent_node']['code']
        out.write(subject + '\t' + predicate_uri + '\t' + str(objcode) + '\n')

        # organ nodes to organ parent
        objcode = parents['organ_level_parent_node']['code']
        for index, row in dforgan.iterrows():
            subject = row['Organ_AZ_code']
            out.write(subject + '\t' + predicate_uri + '\t' + str(objcode) + '\n')

        # cell type annotation assertions
        for index, row in df_crosswalk.iterrows():

            if index >= 0:  # non-header
                if row['Annotation_Label_ID'] is np.nan:
                    continue

                # cell type - is a -> cell type parent
                subject = str(row['Annotation_Label_ID'])
                objcode = parents['cell_annotation_parent_node']['code']
                predicate_uri = "isa"
                out.write(subject + '\t' + predicate_uri + '\t' + str(objcode) + '\n')

                # cell type - located_in -> organ_level code
                objcode = dforgan[dforgan['Organ_Level'] == row['Organ_Level']]['Organ_AZ_code'].iloc[0]
                predicate_uri = 'located_in'
                out.write(subject + '\t' + predicate_uri + '\t' + str(objcode) + '\n')

def write_nodes_file(df: pd.DataFrame, owlnets_dir: str, parents: dict, dforgan: pd.DataFrame, sab:str):

    """
    Writes a nodes file in OWLNETS format.
    :param df: DataFrame from a HRA cell type annotation CSV.
    :param owlnets_dir: output directory
    :param parents: dict of parent nodes
    :param dforgan: DataFrame of organ level node information
    :param sab: sab for annotation
    """

    node_metadata_path: str = os.path.join(owlnets_dir, 'OWLNETS_node_metadata.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(node_metadata_path))

    node_namespace = sab
    with open(node_metadata_path, 'w') as out:
        out.write(
            'node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_definition' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')

        node_definition = ''
        node_synonyms = ''
        node_dbxrefs = ''

        # Define root node
        node_id = parents['parent_node']['code']
        node_label = parents['parent_node']['term']
        out.write(
            node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

        # Define organ level parent node
        node_id = parents['organ_level_parent_node']['code']
        node_label = parents['organ_level_parent_node']['term']
        out.write(
            node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

        # Define organ level parent node
        node_id = parents['cell_annotation_parent_node']['code']
        node_label = parents['cell_annotation_parent_node']['term']
        out.write(
            node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

        # Define organ level nodes
        for index, row in dforgan.iterrows():
            node_id = row['Organ_AZ_code']
            node_label = f"{sab}_{row['Organ_Level']}"
            node_dbxrefs = row['Organ_ID']
            out.write(
                node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

        # Define data nodes
        for index, row in df_crosswalk.iterrows():

            if index >= 0:  # non-header

                if row['Annotation_Label_ID'] is np.nan:
                    continue

                node_id = str(row['Annotation_Label_ID'].strip())

                # Unique term concatenates SAB + organ level + annotation label
                node_label = f"{sab}_{row['Organ_Level'].strip()}_{row['Annotation_Label'].strip()}"

                node_synonyms = row['Annotation_Label'].strip()
                # The synonym field is an optional pipe-delimited list of string values.
                if node_synonyms in (np.nan, 'nan'):
                    node_synonyms = ''

                node_dbxrefs = row['CL_ID'].strip()
                if node_dbxrefs in (np.nan, 'nan'):
                    node_dbxrefs = ''

                out.write(
                    node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

def getargs()->argparse.Namespace:
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description='Builds ontology files in OWLNETS format from a HRA Digital Objects cell annotation spreadsheet.',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("sab", help="Identifier for cell type annotation")
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")
    args = parser.parse_args()

    return args

# -----------------------------------------
# START

args = getargs()

# Read from config file.
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/hra_digital_objects/hra_do.ini')
cfg = uconfig.ubkgConfigParser(cfgfile)

# Get OWL and OWLNETS directories.
# The config file contains absolute paths to the parent directories in the local repo.
# Affix the SAB to the paths.
owl_dir = os.path.join(os.path.dirname(os.getcwd()),cfg.get_value(section='Directories',key='owl_dir'),args.sab)
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()),cfg.get_value(section='Directories',key='owlnets_dir'),args.sab)

if args.skipbuild:
    crosswalk_file = os.path.join(owl_dir,f'{args.sab}_crosswalk.csv')

else:
    # Download the HRA digital object spreadsheet.
    crosswalk_file=download_source_file(cfg=cfg,sab=args.sab,owl_dir=owl_dir,owlnets_dir=owlnets_dir)

# Load cell annotation crosswalk spreadsheet into a DataFrame.
df_crosswalk = pd.read_csv(crosswalk_file,skiprows=10)

# Parent nodes
# crosswalk root
parent_node = {
    "code": f'{args.sab}:0000000',
    "term": f'{args.sab}'
}
# organ level parent
organ_level_parent_node = {
    "code": f'{args.sab}:1000000',
    "term": f'{args.sab}_organ_level'
}
# cell annotation parent
cell_annotation_parent_node = {
    "code": f'{args.sab}:2000000',
    "term": f'{args.sab}_cell_annotation'
}
parents = {
    "parent_node": parent_node,
    "organ_level_parent_node": organ_level_parent_node,
    "cell_annotation_parent_node": cell_annotation_parent_node
}

dforgan = encode_organ_level_nodes(df=df_crosswalk, parents=parents, sab=args.sab)

# Generate the OWLNETS files.
write_nodes_file(df=df_crosswalk, owlnets_dir=owlnets_dir, parents=parents, dforgan=dforgan, sab=args.sab)
write_edges_file(df=df_crosswalk,owlnets_dir=owlnets_dir,parents=parents, dforgan=dforgan, sab=args.sab)


