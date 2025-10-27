#!/usr/bin/env python
# coding: utf-8

# Human Reference Atlas 2D Functional Tissue Unit (FTU) CSV to OWLNETS converter
# 
# Uses a crosswalk spreadsheet available in the Human Reference Atlast to generate a set of
# text files that comply with the
# OWLNETS format.
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
    Reads the 2D FTU CSV.
    :param cfg: an instance of the ubkgConfigParser class, which works with the application configuration file.
                The config file should contain a URL that corresponds to the SimpleKnowledge spreadsheet
                associated with the SAB.
    :param sab: SAB for the annotation file--e.g., FTU
    :param owl_dir: location of downloaded crosswalk files in the local repo
    :param owlnets_dir: location of OWLNETS files in the local repo

    :returns: the full path to the downloaded file

    """

    # Create output folders for source files. Use the existing OWL and OWLNETS folder structure.
    os.system(f'mkdir -p {owl_dir}')
    os.system(f'mkdir -p {owlnets_dir}')

    url = cfg.get_value(section='URL', key='URL')
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    filepath = os.path.join(owl_dir, filename)
    ulog.print_and_logger_info(f'Downloading file {filepath}')
    uextract.download_file(url=url, download_full_path=filepath)

    return filepath

def write_edges_file(df: pd.DataFrame, parents: dict, owlnets_dir: str, sab:str):

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

        # Define root node
        parent_node_id = parents['parent_node']['code']
        parent_node_num = parent_node_id.split(':')[1]

        # Define organ parent
        organ_parent_node_id = parents['organ_parent_node']['code']
        organ_parent_node_num = organ_parent_node_id.split(':')[1]

        # Define ftu parent
        ftu_parent_node_id = parents['ftu_parent_node']['code']
        ftu_parent_node_num = ftu_parent_node_id.split(':')[1]

        # Define ftu part parent
        ftu_part_parent_node_id = parents['ftu_part_parent_node']['code']
        ftu_part_parent_node_num = ftu_part_parent_node_id.split(':')[1]

        # Parent node isa relationships

        predicate_uri = 'isa'
        # organ parent isa parent
        subj = organ_parent_node_id
        obj = parent_node_id
        out.write(subj + '\t' + predicate_uri + '\t' + obj + '\n')
        # ftu parent isa parent
        subj = ftu_parent_node_id
        obj = parent_node_id
        out.write(subj + '\t' + predicate_uri + '\t' + obj + '\n')
        # ftu_part parent is a parent
        subj = ftu_part_parent_node_id
        out.write(subj + '\t' + predicate_uri + '\t' + obj + '\n')

        # The DataFrame is at the level of ftu part, sorted by organ, ftu, and ftu_part.
        # Loop through the DataFrame.

        # Trqcks unique nodes
        organs = []
        ftus = []
        ftu_parts = []

        # Tracks unique relationships
        organ_ftus = {}
        ftu_ftu_parts = {}

        for index, row in df.iterrows():

            predicate_uri = 'isa'

            # Organ isa organ_parent
            organ_label = row['organ_label']
            if organ_label not in organs:
                # Use the row number (index) for the first matching row.
                organ_node_num = int(df.index[df.organ_label == organ_label][0])
                organ_node_id = f'{sab}:{str(int(organ_parent_node_num) + int(organ_node_num) + 1)}'
                subj = organ_node_id
                obj = organ_parent_node_id
                out.write(subj + '\t' + predicate_uri + '\t' + str(obj) + '\n')
                organs.append(organ_label)
                organ_ftus[organ_label] = []

            # FTU isa ftu_parent
            ftu_label = row['ftu_label']
            if ftu_label not in ftus:
                # Use the row number (index) for the first matching row.
                ftu_node_num = int(df.index[df.ftu_label == ftu_label][0])
                ftu_node_id = f'{sab}:{str(int(ftu_parent_node_num) + int(ftu_node_num) + 1)}'
                subj = ftu_node_id
                obj = ftu_parent_node_id
                out.write(subj + '\t' + predicate_uri + '\t' + str(obj) + '\n')
                ftus.append(ftu_label)
                ftu_ftu_parts[ftu_label] = []

            # FTU part isa ftu_part_parent
            ftu_part_label = row['ftu_part_label']
            if ftu_part_label not in ftu_parts:
                # Use the row number (index) for the first matching row.
                ftu_part_node_num = int(df.index[df.ftu_part_label == ftu_part_label][0] + 1)
                ftu_part_node_id = f'{sab}:{str(int(ftu_part_parent_node_num) + int(ftu_part_node_num))}'
                subj = ftu_part_node_id
                obj = ftu_part_parent_node_id
                out.write(subj + '\t' + predicate_uri + '\t' + str(obj) + '\n')
                ftu_parts.append(ftu_part_label)


            # organ has_ftu ftu
            if ftu_node_id not in organ_ftus.get(organ_label):
                subj = organ_node_id
                obj = ftu_node_id
                predicate_uri = "has_ftu"
                out.write(subj + '\t' + predicate_uri + '\t' + str(obj) + '\n')
                organ_ftus.get(organ_label).append(ftu_node_id)

            # ftu has ftu_part ftu_part
            if ftu_part_node_id not in ftu_ftu_parts.get(ftu_label):
                subj = ftu_node_id
                obj = ftu_part_node_id
                predicate_uri = "has_ftu_part"
                out.write(subj + '\t' + predicate_uri + '\t' + str(obj) + '\n')
                ftu_ftu_parts.get(ftu_label).append(ftu_part_node_id)

def write_nodes_file(df: pd.DataFrame, owlnets_dir: str, parents: dict, sab:str):

    """
    Writes a nodes file in OWLNETS format.
    :param df: DataFrame from a HRA cell type annotation CSV.
    :param owlnets_dir: output directory
    :param parents: dict of parent nodes
    :param sab: SAB
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
        parent_node_id = parents['parent_node']['code']
        parent_node_num = parent_node_id.split(':')[1]
        node_label = parents['parent_node']['term']
        out.write(
            parent_node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

        # Define organ parent
        organ_parent_node_id = parents['organ_parent_node']['code']
        organ_parent_node_num = organ_parent_node_id.split(':')[1]
        node_label = parents['organ_parent_node']['term']
        out.write(
            organ_parent_node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

        # Define ftu parent
        ftu_parent_node_id = parents['ftu_parent_node']['code']
        ftu_parent_node_num = ftu_parent_node_id.split(':')[1]
        node_label = parents['ftu_parent_node']['term']
        out.write(
            ftu_parent_node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

        # Define ftu part parent
        ftu_part_parent_node_id = parents['ftu_part_parent_node']['code']
        ftu_part_parent_node_num = ftu_part_parent_node_id.split(':')[1]
        node_label = parents['ftu_part_parent_node']['term']
        out.write(
            ftu_part_parent_node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

        # The DataFrame is at the level of ftu part, sorted by organ, ftu, and ftu_part.
        # Loop through the DataFrame.
        organs = []
        ftus = []
        ftu_parts = []
        node_synonyms = ''

        node_definition = ''
        for index, row in df.iterrows():

            organ_label = row['organ_label']
            if organ_label not in organs:
                # Use the row number (index) of the first match.
                organ_node_num = int(df.index[df.organ_label == organ_label][0])
                organ_node_id = f'{sab}:{str(int(organ_parent_node_num) + int(organ_node_num) + 1)}'
                node_dbxrefs = row['organ_iri'].split('/')[-1].replace('_',':')
                out.write(
                    str(organ_node_id) + '\t' + node_namespace + '\t' + str(organ_label) + '\t' + str(
                        node_definition) + '\t' + str(node_synonyms) + '\t' + str(node_dbxrefs) + '\n')
                organs.append(organ_label)

            ftu_label = row['ftu_label']
            if ftu_label not in ftus:
                # Use the row number (index) of the first match.
                ftu_node_num = int(df.index[df.ftu_label == ftu_label][0])
                ftu_node_id = f'{sab}:{str(int(ftu_parent_node_num) + int(ftu_node_num) + 1)}'
                node_dbxrefs = row['ftu_iri'].split('/')[-1].replace('_',':')
                out.write(
                    str(ftu_node_id) + '\t' + node_namespace + '\t' + str(ftu_label) + '\t' + str(
                        node_definition) + '\t' + str(node_synonyms) + '\t' + str(node_dbxrefs) + '\n')
                ftus.append(ftu_label)

            ftu_part_label = row['ftu_part_label']
            if ftu_part_label not in ftu_parts:
                # Use the row number (index) for the first match.
                ftu_part_node_num = int(df.index[df.ftu_part_label == ftu_part_label][0])
                ftu_part_node_id = f'{sab}:{str(int(ftu_part_parent_node_num) + int(ftu_part_node_num) + 1)}'
                node_dbxrefs = row['ftu_part_iri'].split('/')[-1].replace('_',':')
                out.write(
                    str(ftu_part_node_id) + '\t' + node_namespace + '\t' + str(ftu_part_label) + '\t' + str(
                        node_definition) + '\t' + str(node_synonyms) + '\t' + str(node_dbxrefs) + '\n')
                ftu_parts.append(ftu_part_label)

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

def getargs()->argparse.Namespace:
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description='Builds ontology files in OWLNETS format from the HRA 2D FTU spreadsheet.',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("sab", help="Identifier for cell type annotation")
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")
    args = parser.parse_args()

    return args


def getparentnodes(sab:str)->dict:

    """
    Mints node IDs for the parent nodes of the FTU2D ontology.
    :param sab: the SAB
    :return:
    """

    parent_node = {
        "code": f'{args.sab}:000000',
        "term": f'{args.sab}'
    }
    # organ parent
    organ_parent_node = {
        "code": f'{args.sab}:100000',
        "term": f'{args.sab} organ'
    }
    # ftu parent
    ftu_parent_node = {
        "code": f'{args.sab}:200000',
        "term": f'{args.sab} ftu'
    }
    # ftu part
    ftu_part_parent_node = {
        "code": f'{args.sab}:300000',
        "term": f'{args.sab} ftu_part'
    }

    return {
        "parent_node": parent_node,
        "organ_parent_node": organ_parent_node,
        "ftu_parent_node": ftu_parent_node,
        "ftu_part_parent_node": ftu_part_parent_node
    }

# -----------------------------------------
# START

args = getargs()

# Read from config file.
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/ftu2d/ftu2d.ini')
cfg = uconfig.ubkgConfigParser(cfgfile)

# Get OWL and OWLNETS directories.
# The config file contains absolute paths to the parent directories in the local repo.
# Affix the SAB to the paths.
owl_dir = os.path.join(os.path.dirname(os.getcwd()),cfg.get_value(section='Directories',key='owl_dir'),args.sab)
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()),cfg.get_value(section='Directories',key='owlnets_dir'),args.sab)

if args.skipbuild:
    crosswalk_file = os.path.join(owl_dir,'2d-ftu-parts.csv')

else:
    # Download the HRA digital object spreadsheet.
    crosswalk_file=download_source_file(cfg=cfg,sab=args.sab,owl_dir=owl_dir,owlnets_dir=owlnets_dir)

# Load cell annotation crosswalk spreadsheet into a DataFrame.
df_crosswalk = pd.read_csv(crosswalk_file)

# Sort DataFrame by organ, ftu, ftu_part
df_crosswalk_sorted = df_crosswalk.sort_values(['organ_label','ftu_label','ftu_part_label'])

# Parent nodes
parents = getparentnodes(args.sab)

# Generate the OWLNETS files.
write_nodes_file(df=df_crosswalk_sorted, owlnets_dir=owlnets_dir, parents=parents, sab=args.sab)
write_edges_file(df=df_crosswalk_sorted, owlnets_dir=owlnets_dir, parents=parents, sab=args.sab)

