#!/usr/bin/env python
# coding: utf-8

# Unified Biomedical Knowledge Graph
# Script to ingest Reactome data
# January 2025

import os
import sys

import argparse
from tqdm import tqdm
import requests
import pandas as pd
import numpy as np
import json

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

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

def getargs() -> argparse.Namespace:

    # Parse arguments.
    parser = argparse.ArgumentParser(
    description='Convert REACTOME data to OWLNETs.\n'
                'In general you should not have the change any of the optional arguments.',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
    # positional arguments
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")
    args = parser.parse_args()

    return args

def gethierarchyedges(dictevent:dict, taxon: str)->list:
    """
    Builds a list of hierarchical assertions for a PathwayBrowserNode object ("node"), recursing through the node's
    nested child nodes.

    :param dictevent: dictionary representing PathwayBrowserNode
    :param taxon: NCBI taxon id for species
    :return: list of hierarchical assertions.
    """
    listret = []

    # Assert class ("isa" edge) for the node in the hierarchy.
    # TO DO: valueset of parent codes for event types--e.g., REACTOME:xxxxx for 'TopLevelPathway'
    dictedge = {'subject': dictevent.get('stId'), 'predicate': 'isa', 'object': dictevent.get('type')}

    listret.append(dictedge)
    # Build assertions for child nodes.
    listchildren = dictevent.get('children')
    if listchildren is not None:
        for child in listchildren:
            # Emulate the "hasEvent" relationship of the Reactome (graph) model.
            dictedge = {'subject': dictevent.get('stId'), 'predicate': 'has_event', 'object': child.get('stId')}
            listret.append(dictedge)
            # Obtain hierarchy list for child node.
            listchildhierarchy = gethierarchyedges(dictevent=child, taxon=taxon)
            # Merge the child list to the parent list, instead of appending it.
            listret = listret + listchildhierarchy

    return listret

def getspeciesedges(base_url: str, species_id:str) -> list:

    """
    Builds a set of edge assertions for a species.

    Two basic types of assertions will be obtained from Reactome:
    1. Hierarchical - i.e., those that describe the Reactome "event hierarchy":
       TopLevelPathway
       -- Pathway
          -- Reaction or Blackbox Event
    2. Property

    Hierarchical edges:
    The eventsHierarchy endpoint of the Reactome Content Services API returns for a species a list of "tree structures", or
    nested dictionaries. Each dictionary in the list (a "PathwayBrowserNode object" in the Reactome model) can contain a "children"
    object, itself a list of PathwayBrowernode objects. Translating an event hierarchy requires recursion through the generations of PathwayBrowserNode objects.

    :param base_url: base URL for Reactome Content Services API
    :param speciesid: NCBI Taxon ID for a species.
    :return: list of edge assertions for the species.
    """
    # Get hierarchical data for the species from the Reactome Content Service API.
    url = base_url + f'eventsHierarchy/{species_id}?pathwaysOnly=false&resource=TOTAL&interactors=false&importableOnly=false'
    response = requests.get(url)
    if response.status_code != 200:
        response.raise_for_status()

    listevent = response.json()
    listedges = []

    # Traverse the event hierarchy, starting at the level of TopLevelPathway.
    for dictevent in listevent:
        # Build hierarchical edges for each top level event. Merge lists instead of appending them.
        listedges = listedges + gethierarchyedges(dictevent=dictevent,taxon=species_id)

    # Add property edges.
    listedges = listedges + getpropertyedges(listhierarchyedges=listedges, species_id=species_id)
    return listedges

def getpropertyedges(listhierarchyedges:list, species_id: str) -> list:
    """
    Builds property assertions for Reactome events
    :param listhierachyedges: a list of Reactome events from the event hierarchy for a species
    :param species_id: NCBI Taxon code for the species
    :return:
    """
    listpropertyedges = []

    for event in listhierarchyedges:
        # Each list element is a dictionary with schema
        # {
        #   'subject': <Reactome stable identifier>,
        #   'predicate': <relationship>,
        #   'object': <Reactome stable identifier>
        # ?

        # Assert species for event.
        pred = 'http://purl.obolibrary.org/obo/RO_0002162'  # in_taxon
        dictedge = {'subject': event.get('subject'), 'predicate': pred, 'object': f'NCIT:{species_id}'}
        listpropertyedges.append(dictedge)

    return listpropertyedges

def getallspeciesedges(cfg: uconfig.ubkgConfigParser, owlnets_dir: str) -> pd.DataFrame:
    """
    Build edges for a set of specified species.

    :param cfg: application configuration file, which includes a list of species
    :param owlnets_dir: directory in which to write OWLNETS edge and node files
    :return: a dataframe representing edge assertions
    """

    listallspeciesedges = []
    base_url = cfg.get_value(section='URL', key='base_url')

    # For each species indicated in the config file, obtain lists of assertions.
    for species in cfg.config['Species']:
        species_id = cfg.get_value(section='Species', key=species)
        ulog.print_and_logger_info(f'Building edges for species={species_id} ({species})...')
        # Add the list of assertions for the species. Merge lists instead of append.
        listallspeciesedges = listallspeciesedges + getspeciesedges(base_url=base_url, species_id=species_id)

    # Convert list of assertions to a DataFrame.
    dfedges = pd.DataFrame(listallspeciesedges)
    return dfedges

# -----------------------------
# MAIN

# Process optional arguments, including -s (skip)
args = getargs()

# Read from config file
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/reactome/reactome.ini')
config = uconfig.ubkgConfigParser(cfgfile)

# Get OWL and OWLNETS directories.
# The config file should contain absolute paths to the directories.
owl_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owl_dir'))
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owlnets_dir'))

# Get Reactome source files.
if args.skipbuild:
    # Read previously downloaded file.
    #filepath = os.path.join(os.path.join(owlnets_dir, 'UNIPROTKB_all.tsv'))
    #dfUNIPROT = uextract.read_csv_with_progress_bar(filepath, sep='\t')
    #dfUNIPROT = dfUNIPROT.replace(np.nan, '', regex=True)
    print('skipping')
else:
    #Build the edges for the specified set of species
    dfeventedges = getallspeciesedges(cfg=config, owlnets_dir=owlnets_dir)
    ftest = os.path.join(owlnets_dir, 'hierarchy_edges.csv')
    dfeventedges.to_csv(ftest)

print('DEBUG: exit')
exit(1)