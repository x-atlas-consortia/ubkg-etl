#!/usr/bin/env python
"""
cedar_entity

initial version: February 2024

UBKG ETL that maps templates from CEDAR to HuBMAP/SenNet provenance entities.

Assumes that the following SABs have already been ingested into the ontology CSVs.
CEDAR
HUBMAP
SENNET

"""

import sys
import os

import numpy as np
import pandas as pd

# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path. (This assumes that this script is being called from build_csv.py.)
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)

# Logging module
import ubkg_logging as ulog
# Config file
import ubkg_config as uconfig


def initialize_file(path: str, file_type: str):
    """
    Creates and writes header for edge and node file.

    :param path: path to edge file
    :param file_type: edge or node
    :return:
    """

    ulog.print_and_logger_info('Building: ' + os.path.abspath(path))

    if file_type == 'edge':
        header = 'subject\tpredicate\tobject\n'
    else:
        header = 'node_id\tnode_namespace\tnode_label\tnode_definition\tnode_synonyms\tnode_dbxrefs\n'

    with open(path, 'w') as out:
        out.write(header)

    return

# --------------------------------


cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/cedar_entity/cedar_entity.ini')
config = uconfig.ubkgConfigParser(cfgfile)

owlnets_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owlnets_dir'))
owlnets_dir_sab = os.path.join(owlnets_dir, 'CEDAR_ENTITY')

# Make the output directory.
os.system(f'mkdir -p {owlnets_dir_sab}')

# Get the appropriate file path. Assume that CEDAR has been ingested.
frompath = config.get_value(section='Paths', key='CEDAR')

# Read the CEDAR edge file.
dfcedaredge = pd.read_csv(frompath, delimiter='\t')
# Filter the CEDAR edge file to those nodes that are children of the template parent.
dftemplate = dfcedaredge[dfcedaredge['object'] == 'https://schema.metadatacenter.org/core/Template']

# Build list of CEDAR template node ids.
listcedarids = []
for index, row in dftemplate.iterrows():
    idsplit = row['subject'].split('/')
    listcedarids.append(f'CEDAR:{idsplit[len(idsplit)-1]}')


# BUILD THE NODE FILE.
# Initialize the node file.
nodes_path: str = os.path.join(owlnets_dir_sab, 'OWLNETS_node_metadata.txt')
ulog.print_and_logger_info(f'Writing nodes file at {nodes_path}...')
initialize_file(path=nodes_path, file_type='node')

# Write CEDAR template node ids to the node file. This assumes that CEDAR has already been ingested.
with open(nodes_path, 'a') as out:
    for lid in listcedarids:
        node_id = lid
        out.write(f'{node_id}\n')

# BUILD THE EDGE FILE.
# Initialize the edge file.
edgelist_path: str = os.path.join(owlnets_dir_sab, 'OWLNETS_edgelist.txt')
ulog.print_and_logger_info(f'Writing edge file to {edgelist_path}...')
initialize_file(path=edgelist_path, file_type='edge')

# Read the map of templates that do not map to dataset.
map_path: str = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/cedar_entity/cedar_entity.tsv')
dfmap = pd.read_csv(map_path, delimiter='\t')

# Write 'used_in_entity' relationships between each CEDAR template node and the appropriate provenance entities in
# HuBMAP and SenNet.

with open(edgelist_path, 'a') as out:
    for id in listcedarids:
        subject = id
        predicate = 'used_in_entity'
        dftest = dfmap[dfmap['id'] == id]
        if dftest.empty:
            # dataset entities
            # HUBMAP:C040001
            # SENNET:C050002
            obj = 'HUBMAP:C040001'
            out.write(f'{subject}\t{predicate}\t{obj}\n')
            obj = 'SENNET:C050002'
            out.write(f'{subject}\t{predicate}\t{obj}\n')
        else:
            obj = dftest.iloc[0]['hubmap']
            if obj is not np.nan:
                out.write(f'{subject}\t{predicate}\t{obj}\n')
            obj = dftest.iloc[0]['sennet']
            if obj is not np.nan:
                out.write(f'{subject}\t{predicate}\t{obj}\n')
