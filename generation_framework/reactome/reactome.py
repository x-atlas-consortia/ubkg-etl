#!/usr/bin/env python
# coding: utf-8

# Unified Biomedical Knowledge Graph
# Script to ingest Reactome data
# January 2025

import os
import sys
#import time

import argparse
from tqdm import tqdm
import requests
import pandas as pd

# Import UBKG utilities which is in a directory that is at the same level as the script directory.
# Go "up and over" for an absolute path.
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)
# Logging module
import ubkg_logging as ulog
import ubkg_config as uconfig
# Extraction module
import ubkg_extract as uextract
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
    argsret = parser.parse_args()

    return argsret

def getcodefromvalueset(val: str, df_vs:pd.DataFrame) -> str:
    """
    Obtains a code from the REACTOME_VS valueset.
    :param val: Value corresponding to a potential node_label of the code in the REACTOME_VS valueset.
    :param df_vis: REACTOME_VS valueset
    :return: code from the valueset.
    """

    if df_vs.loc[df_vs['node_label'] == val, 'node_id'].shape[0] > 0:
        return str(df_vs.loc[df_vs['node_label'] == val, 'node_id'].iat[0])


def gethierarchyedges(dictevent:dict, taxon: str, df_vs: pd.DataFrame)->list:
    """
    Builds a list of hierarchical assertions for an Reactome event (a PathwayBrowserNode object or "node"),
    recursing through the node's nested child nodes.

    :param dictevent: dictionary representing an event
    :param taxon: NCBI taxon id for species
    :param df_vs: valueset from REACTOME_VS ingestion
    :return: list of hierarchical assertions.
    """
    listret = []

    # Assert class ("isa" edge) for the node in the hierarchy.
    dictedge = {'subject': f'REACTOME:{dictevent.get("stId")}',
                'predicate': 'isa',
                'object': getcodefromvalueset(val=dictevent.get('type'),df_vs=df_vs)}

    listret.append(dictedge)
    # Build assertions for child nodes.
    listchildren = dictevent.get('children')
    if listchildren is not None:
        for child in listchildren:
            # Emulate the "hasEvent" relationship of the Reactome (graph) model.
            pred = 'http://purl.obolibrary.org/obo/RO_0002410' # causally_related_to
            dictedge = {'subject': f'REACTOME:{dictevent.get("stId")}', 'predicate': pred, 'object': f'REACTOME:{child.get("stId")}'}
            listret.append(dictedge)
            # Obtain hierarchy list for child node.
            listchildhierarchy = gethierarchyedges(dictevent=child, taxon=taxon, df_vs=df_vs)
            # Merge the child list to the parent list, instead of appending it.
            listret = listret + listchildhierarchy

    return listret

def getspeciesedges(base_url: str, species_id:str, df_vs:pd.DataFrame) -> list:

    """
    Builds a set of edge assertions for a species.

    Two basic types of assertions will be obtained from Reactome:
    1. Hierarchical - i.e., those that describe the Reactome "event hierarchy":
       TopLevelPathway
       -- Pathway
          -- ReactionTypeEvent (e.g., Reaction)
    2. Property - i.e., associations between events and information such as species; GO annotations; and participants

    Hierarchical edges:
    The eventsHierarchy endpoint of the Reactome Content Services API returns for a species a list of "tree structures", or
    nested dictionaries. Each dictionary in the list (a "PathwayBrowserNode object" in the Reactome model) can contain a "children"
    object, itself a list of PathwayBrowernode objects. Translating an event hierarchy requires recursion through the generations of PathwayBrowserNode objects.

    :param base_url: base URL for Reactome Content Services API
    :param species_id: NCBI Taxon ID for a species.
    :param df_vs: valueset from REACTOME_VS ingestion.
    :return: list of edge assertions for the species.
    """
    # Get hierarchical data for the species from the Reactome Content Service API.
    url = base_url + f'eventsHierarchy/{species_id}?pathwaysOnly=false&resource=TOTAL&interactors=false&importableOnly=false'
    listevent = uextract.getresponsejson(url)
    listedges = []

    ulog.print_and_logger_info('Building hierarchy edges...')
    # Traverse the event hierarchy, starting at the level of TopLevelPathway.
    for dictevent in tqdm(listevent):
        # Build hierarchical edges for each top level event. Merge lists instead of appending them.
        listedges = listedges + gethierarchyedges(dictevent=dictevent,taxon=species_id, df_vs=df_vs)

    # Add property edges.
    ulog.print_and_logger_info('Building property edges...')
    listedges = listedges + getpropertyedges(listhierarchyedges=listedges, base_url=base_url, species_id=species_id)
    return listedges

def getpropertyedges(listhierarchyedges:list, base_url: str, species_id: str) -> list:
    """
    Builds property assertions for Reactome events, including:
    1. taxon
    2. GO cellular component (also described as "compartment" in the Reactome data model
    3. GO biological process
    4. preceding events
    5. physical entities (proteins, chemicals, transcripts)

    :param listhierarchyedges: a list of Reactome events from the event hierarchy for a species
    :param species_id: NCBI Taxon code for the species
    :param base_url: base URL for Reactome Content Services API
    :return:
    """
    listpropertyedges = []

    # Obtain a unique list of Reactome identifiers.
    dfedges=pd.DataFrame(listhierarchyedges)
    listuniqueids = dfedges['subject'].drop_duplicates().to_list()

    ulog.print_and_logger_info('Edges for species, GO, preceding events...')
    #idebug = 0
    for id in tqdm(listuniqueids):

        #idebug = idebug + 1
        #if idebug == 21:
            #break

        # Each list element is a dictionary with schema
        # {
        #   'subject': <Reactome stable identifier>,
        #   'predicate': <relationship>, preferably one defined in Relations Ontology
        #   'object':
        #       <Reactome stable identifier> for hierarchical edges
        #       <code for an object in a vocabulary--e.g., GO; UniProtKB; CHEBI; Reactome>
        # }

        # SPECIES
        pred = 'http://purl.obolibrary.org/obo/RO_0002162'  # in_taxon
        listpropertyedges.append({'subject': id, 'predicate': pred, 'object': f'NCIT:{species_id}'})

        # Call the https://reactome.org/ContentService/data/query/enhanced endpoint.
        # Remove the SAB from the code for the event.
        url = base_url + f'query/enhanced/{id.replace("REACTOME:","")}'
        queryjson = uextract.getresponsejson(url)

        # GO biological process
        # Per the Gene Ontology Annotation (GOA) documentation, the default relationship for the Biological Process
        # aspect of GO is "involved_in".
        pred = 'http://purl.obolibrary.org/obo/RO_0002331' # involved_in
        go_biological_process = queryjson.get('goBiologicalProcess')
        if go_biological_process is not None:
            obj = 'GO:' + go_biological_process.get('accession')
            listpropertyedges.append({'subject': id, 'predicate': pred, 'object': obj})

        # compartment (GO cellular component)
        # Per GOA, the default relationship for the Cellular Component aspect is "part_of".
        pred = 'http://purl.obolibrary.org/obo/BFO_0000050' #part_of
        compartment = (queryjson.get('compartment'))
        if compartment is not None:
            for c in compartment:
                obj = 'GO:' + c.get('accession')
                listpropertyedges.append({'subject': id, 'predicate': pred, 'object': obj})

        # preceding events
        pred = 'http://purl.obolibrary.org/obo/BFO_0000062' # preceded_by
        preceding_event = queryjson.get('precedingEvent')
        if preceding_event is not None:
            for p in preceding_event:
                # Preceding events are sometimes simple IDs.
                if type(p) is dict:
                    obj = p.get('stId')
                    listpropertyedges.append({'subject': id, 'predicate': pred, 'object': f'REACTOME:{obj}'})

    # List of Physical Entity participant edges.
    # In the Reactome event hierarchy, Events that are subclasses of ReactionTypeEvents have physical entities;
    # however, the Content Services API is recursive--i.e., it returns for an event the physical entities for all
    # events that have a causal relationship with the event.
    # To prevent duplication from recursion, only link physical entities to subclasses of ReactionTypeEvents.
    dfreactions = dfedges[dfedges['object'].isin(['REACTOME_VS:C0006', #BlackBoxEvent
                                                  'REACTOME_VS:C0007', #CellDevelopmentStep
                                                  'REACTOME_VS:C0008', #Depolymerization
                                                  'REACTOME_VS:C0009', #FailedReaction
                                                  'REACTOME_VS:C0010', #Polymerization
                                                  'REACTOME_VS:C0011'])] # Reaction


    listreactionids = dfreactions['subject'].to_list()
    ulog.print_and_logger_info('Physical Entity edges...')

    #idebug = 0
    for rid in tqdm(listreactionids):
        #idebug = idebug + 1
        #if idebug == 21:
            #break
        # Merge the participant edge list with the edge list instead of appending it.
        listpropertyedges = listpropertyedges + getparticipantedges(base_url=base_url, event_id=rid)

    return listpropertyedges

def getparticipantedges(base_url: str, event_id: str) -> list:
    """
    Builds a list of edges that describe the "participants" in a Reactome event--proteins or chemicals.

    Skip the intermediate levels of Reactome complexes (or "Physical entities") and go down
    to the gene product (UniProtKB) or molecule (CHEBI, ENSEMBL) ("Reference entities").

    :param base_url: base URL for Reactome Content Services API
    :param event_id: Reactome stable ID for an event.
    """
    # Call the referenceEntities endpoint.
    url = base_url + f'participants/{event_id.replace("REACTOME:","")}/referenceEntities'
    participantjson = uextract.getresponsejson(url)
    listedges = []
    if participantjson is not None:
        for p in participantjson:
            pred = 'http://purl.obolibrary.org/obo/RO_0000057' # has_participant
            classname = p.get('className')
            if classname == 'ReferenceGeneProduct':
                # The SAB for UniProt in UBKG is UNIPROTKB.
                sab = 'UNIPROTKB'
            else:
                sab = p.get('databaseName').upper()
            obj = f'{sab}:{p.get("identifier")}'
            listedges.append({'subject': event_id, 'predicate': pred, 'object': obj})
    return listedges

def getallspeciesedges(cfg: uconfig.ubkgConfigParser, df_vs: pd.DataFrame) -> pd.DataFrame:
    """
    Build edges for a set of specified species.

    :param cfg: application configuration object, which includes a list of species
    :param df_vs: DataFrame of the REACTOME_VS valueset.

    :return: a dataframe representing edge assertions
    """

    listallspeciesedges = []
    base_url = cfg.get_value(section='URL', key='base_url')

    # For each species indicated in the config file, obtain lists of assertions.
    for species in cfg.config['Species']:
        species_id = cfg.get_value(section='Species', key=species)
        ulog.print_and_logger_info(f'Building edges for species={species_id} ({species})...')
        # Add the list of assertions for the species. Merge lists instead of append.
        listallspeciesedges = listallspeciesedges + getspeciesedges(base_url=base_url, species_id=species_id, df_vs=df_vs)

    # Convert list of assertions to a DataFrame.
    dfret = pd.DataFrame(listallspeciesedges)
    return dfret

def getnodesfromedges(cfg: uconfig.ubkgConfigParser, df:pd.DataFrame) -> pd.DataFrame:
    """
    Builds a set of unique nodes.

    :param cfg: application configuration object
    :param df: DataFrame of assertions. This should be the DataFrame that corresponds to the edge file.
    :return: DataFrame of node information
    """

    # Algorithm:
    # Get unique list of Reactome stable IDs for nodes.
    # For each node in the list,
    #    - Call Reactome Content Services API query/advanced endpoint to obtain a set of information on the node.
    #    - Obtain information for node file:
    #        - Preferred term
    #        - Description
    #        - Synonyms
    #    - Append to list.
    # Build DataFrame.

    # node_id	node_namespace	node_label	node_definition	node_synonyms	node_dbxrefs
    ulog.print_and_logger_info('Building nodes...')

    # Because the set of assertions in the input DataFrame includes those of the Reactome event hierarchy,
    # all relevant Reactome stable IDs should be in the "subject" column.
    listreactomeids = df['subject'].drop_duplicates().to_list()
    base_url = cfg.get_value(section='URL', key='base_url')
    listnodes = []

    #idebug = 0
    for node_id in tqdm(listreactomeids):

        #idebug = idebug + 1
        #if idebug == 21:
            #break

        # Remove the REACTOME SAB from the ID.
        url = base_url + f'query/enhanced/{node_id.replace("REACTOME:", "")}'
        queryjson = uextract.getresponsejson(url)
        node_label = queryjson.get('displayName','')
        summation = queryjson.get('summation')
        node_definition = ''
        if summation is not None:
            # The 'text' field contains too much data to be read into a column in a DataFrame.
            # Use the excerpted field 'displayName'.
            node_definition = summation[0].get('displayName','')

        listnodes.append({'node_id':node_id,
                          'node_namespace': 'REACTOME',
                          'node_label': node_label,
                          'node_definition': node_definition,
                          'node_dbxref':''})

    dfret = pd.DataFrame(listnodes)
    return dfret

def getvs(path: str) -> pd.DataFrame:

    # Responses from the Reactome Content Services API have values that have been encoded as nodes in the REACTOME_VS
    # set of assertions.
    # Load the nodes file related to the prior ingestion.

    nodefile = os.path.join(path, 'OWLNETS_node_metadata.txt')

    try:
        return uextract.read_csv_with_progress_bar(nodefile, sep='\t')
    except FileNotFoundError:
        ulog.print_and_logger_info('REACTOME depends on the prior ingestion of information '
                                   'from the REACTOME_VS SAB. Run .build_csv.sh for REACTOME_VS prior '
                                   'to running it for REACTOME.')
        exit(1)


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
vs_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='vs_dir'))

# Get Reactome source files.
if not args.skipbuild:

    # Obtain the REACTOME_VS valueset.
    df_vs = getvs(vs_dir)

    # Build the edges for the specified set of species.
    dfedges = getallspeciesedges(cfg=config, df_vs=df_vs)

    # Build the nodes file, using the edge DataFrame.
    dfnodes = getnodesfromedges(cfg=config, df=dfedges)

    # Write edges to file.
    dfedges = dfedges[['subject', 'predicate', 'object']]
    fout = os.path.join(owlnets_dir, 'edges.tsv')
    dfedges.to_csv(fout, sep='\t', index=False)

    # Write nodes to file.
    dfnodes = dfnodes[['node_id', 'node_namespace', 'node_label', 'node_definition', 'node_dbxref']]
    fout = os.path.join(owlnets_dir, 'nodes.tsv')
    dfnodes.to_csv(fout, sep='\t', index=False)

