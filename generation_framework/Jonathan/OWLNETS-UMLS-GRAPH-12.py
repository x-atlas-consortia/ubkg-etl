#!/usr/bin/env python
# coding: utf-8

# OCTOBER 2022
# JAS
# THIS VERSION OF THE SCRIPT (OWLNETS-UMLS-GRAPH-12.py) IS THE SCRIPT OF RECORD.
# ENHANCEMENTS OR BUG FIXES SHOULD BE MADE DIRECTLY TO THIS SCRIPT.

# In other words, the method of updating a Jupyter notebook to a new version and then
# running the transform script to convert the notebook to a pure Python script has been deprecated.
# "Version 12" of the script is the source of coding truth.
#
# Potential enhancements:
# 1. Rename the script.
# 2. Add Python logging.

# -----------------------------------------------------

# # OWLNETS-UMLS-GRAPH

# ## Adds OWLNETS output files content to existing UMLS-Graph-Extracts

# ### Setup

# In[1]:

# JAS 6 JANUARY 2023
# Changes to accommodate files provided in UBKG edges/nodes format. The format includes optional
# columns in the edges and nodes files.

import sys
import pandas as pd
import numpy as np
import base64
import json
import os
import fileinput

# JAS FEB 2023
# The codeReplacements function was originally part of this script. Because the function is now
# needed by both this script and the skowlnets.py script, the function has been moved to the module
# scripts/ubkg_utilities/parsetools.py.
# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path. (This assumes that this script is being called from build_csv.py.)
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath,'scripts/ubkg_utilities')
sys.path.append(fpath)
import parsetools

def owlnets_path(file: str) -> str:
    return os.path.join(sys.argv[1], file)


def csv_path(file: str) -> str:
    return os.path.join(sys.argv[2], file)

def identify_source_file(file_names: list) -> str:
    # Checks for the existence of source files (edges or nodes).

    # Source files can be named in various ways--e.g., OWLNETS_node_metadata.txt, nodes.tsv, nodes.txt

    for f in file_names:
        if os.path.exists(owlnets_path(f)):
            return f

    # Error case: no file found with name in argument list.
    lfile = ','.join(str(f) for f in file_names)
    raise FileNotFoundError('No file found with name in list: ' + lfile)

def update_columns_to_csv_header(file: str, new_columns: list):
    # JAS 6 January 2023
    # Updates the header of a CSV file, adding new column names.

    for line in fileinput.input(file, inplace=True):
        if fileinput.isfirstline():
            # Replace the header with the columns from the argument list.
            newline = ','.join(new_columns)
        else:
            # Strip the newline from the end of the current row and then reprint it.
            newline = line.rstrip('\n')
        print(newline)
    return


# Asssignnment of SAB for CUI-CUI relationships (edgelist) - typically use file name before .owl in CAPS
OWL_SAB = sys.argv[3].upper()

# JAS 15 NOV 2022 - removed organism argument, because we are not ingesting PR.
# JAS 19 OCT 2022
# Organism argument, which factors for ingestion of the PR ontology.
# ORGANISM = sys.argv[4].lower()

# TO DO: Use argparse instead of sys.argv

pd.set_option('display.max_colwidth', None)

# ### Ingest OWLNETS output files, remove NaN and duplicate (keys) if they were to exist

# In[2]:

print('Reading OWLNETS files for ontology...')

# JAS 6 JAN 2023
# The node file will be in one of two formats:
# 1. OWLNETS
# 2. UBKG edge/nodes

nodefilelist = ['OWLNETS_node_metadata.txt','nodes.txt','nodes.tsv']
nodepath = identify_source_file(nodefilelist)

# JAS 6 JAN 2023 add optional columns (value, lowerbound, upperbound, unit) for UBKG edges/nodes files.
# JAS 6 JAN 2023 skip bad rows. (There is at least one in line 6814 of the node_metadata file generated from EFO.)
node_metadata = pd.read_csv(owlnets_path(nodepath), sep='\t', on_bad_lines='skip')
if 'value' not in node_metadata.columns:
    node_metadata['value'] = np.nan
    node_metadata['lowerbound'] = np.nan
    node_metadata['upperbound'] = np.nan
    node_metadata['unit'] = np.nan
# JAS Feb 2023 ignore 'node_namespace'.
#node_metadata = node_metadata[['node_id', 'node_namespace', 'node_label', 'node_definition', 'node_synonyms',
                               #'node_dbxrefs', 'value', 'lowerbound', 'upperbound', 'unit']]
node_metadata = node_metadata[['node_id', 'node_label', 'node_definition', 'node_synonyms',
                               'node_dbxrefs', 'value', 'lowerbound', 'upperbound', 'unit']]

node_metadata = node_metadata.replace({'None': np.nan})
node_metadata = node_metadata.dropna(subset=['node_id']).drop_duplicates(subset='node_id').reset_index(drop=True)

# In[3]:

# JAS 8 Nov 2022
# The OWLNETS_relations.txt file is no longer required; however, if it is available, it will contain information for
# relation properties that are defined outside the Relations Ontology.
#
# Obtain relationship information as follows:
# 1. If a relations file is available (e.g., as output from PheKnowLator), obtain
# relationship label information from it.
# 2. If no relations file is available, obtain relationship information from the
# OWLNETS_edgelist.txt.
#
# An edge in edgelist is one of the following types:
# 1. an IRI that corresponds to the IRI of a relationship property from the Relations Ontology (RO)
# 2. a subClassOf relationship, that will be translated to isa
# 3. a text string that matches a relationship label in RO--i.e., a weaker link to RO than by IRI.
# 4. a text string that does not match a relationship label in RO.
#    This can either be a relationship that is defined with an IRI not in RO or a
#    custom string.
# Possible enhancement: identify relationship properties outside of RO. This would entail finding
# equivalents of ro.json, or perhaps some form of API call.

relations_file_exists = os.path.exists(owlnets_path('OWLNETS_relations.txt'))

if relations_file_exists:
    print('Obtaining relations data from relations metadata file.')
    relations = pd.read_csv(owlnets_path("OWLNETS_relations.txt"), sep='\t')
    relations = relations.replace({'None': np.nan})
    relations = relations.dropna(subset=['relation_id']).drop_duplicates(subset='relation_id').reset_index(drop=True)
    # handle relations with no label by inserting part after # - may warrant more robust solution or a hard stop
    relations.loc[relations['relation_label'].isnull(), 'relation_label'] = relations['relation_id'].str.split('#').str[
        -1]
else:
    print('No relations metadata found, so obtaining relations data from edgelist file.')

# In[4]:

# JAS 6 JAN 2023
# The edgelist file will be in one of two formats:
# 1. OWLNETS
# 2. UBKG edge/nodes

edgefilelist = ['OWLNETS_edgelist.txt','edges.txt','edges.tsv']
edgepath = identify_source_file(edgefilelist)

# JAS 6 JAN 2023 - add evidence_class; limit columns.
edgelist = pd.read_csv(owlnets_path(edgepath), sep='\t')
if 'evidence_class' not in edgelist.columns:
    edgelist['evidence_class'] = np.nan
edgelist = edgelist[['subject', 'predicate', 'object', 'evidence_class']]

# JAS 6 JAN 2023 - Add subset because evidence_class is optional.
subset = ['subject', 'predicate', 'object']
edgelist = edgelist.dropna(subset=subset).drop_duplicates(subset=subset).reset_index(drop=True)
edgelist = edgelist.replace({'None': np.nan})
# #### Delete self-referential edges in edgelist - CUI self-reference also avoided (later) by unique CUIs for node_ids

# In[5]:

edgelist = edgelist[edgelist['subject'] != edgelist['object']].reset_index(drop=True)

# JAS 20 OCT 2022
# The OWLNETS files for PR are large enough to cause the script to run out of memory in the CUI assignments.
# So, a hack and a logging solution:
# 1. For PR, only select those nodes for the ORGANISM specified in the optional argument
#    (e.g., human, mouse).
#    This will require text searching, and so is a hack that depends on the node description field
#    containing a key word.
# 2. Show counts of rows and warn for large files.

edgecount = len(edgelist.index)
nodecount = len(node_metadata.index)

print('Number of edges in edgelist.txt:', edgecount)
print('Number of nodes in node_metadata.txt', nodecount)

if edgecount > 500000 or nodecount > 500000:
    print('WARNING: Large OWLNETS files may cause the script to terminate from memory issues.')


# JAS 15 NOV 2022
# Deprecating checks related to PR.
# --------
# if OWL_SAB == 'PR':
# if ORGANISM == '':
# The script will fail. Exit gracefully.
# raise SystemExit('Because of the size of the PR ontology, it is necessary to specify a species. Use the '
# '-p parameter in the call to the generation script.')
# print(
# f'For the PR ontology, this script will select a subset of nodes that correspond to proteins that are '
# f'unambiguously for the organism: {ORGANISM}.')

# Case-insensitive search of the node definition, ignoring null values.
# node_metadata = node_metadata[
# node_metadata['node_definition'].fillna(value='').str.lower().str.contains(ORGANISM.lower())]
# nodecount = len(node_metadata.index)
# print(f'Node count for {ORGANISM}:{nodecount}')
# ---------

# JAS FEBRUARY 2023
# Move the codeReplacements function to the ubkg_utilities/parsetools.py module

# ### Join relation_label in edgelist, convert subClassOf to isa and space to _, CodeID formatting

# In[7]:
print('Establishing edges and inverse edges...')

# JAS 8 Nov 2022
# The OWLNETS_relations.txt file is no longer required; however, if it is available, it will contain information for
# relation properties that are defined outside the Relations Ontology.

if relations_file_exists:
    # Obtain the relation label from the relations file.
    # This can correspond to:
    # 1. The label for a relationship property in RO.
    # 2. The label for a relationship not defined in RO, including relationships defined in
    #    other ontologies.
    # JAS 6 JAN 2023 Add evidence_class
    edgelist = edgelist.merge(relations, how='left', left_on='predicate', right_on='relation_id')
    edgelist = edgelist[['subject', 'predicate', 'object', 'relation_label', 'evidence_class']].rename(
        columns={"relation_label": "relation_label_from_file"})
else:
    edgelist['relation_label_from_file'] = np.NaN
# del relations

# JAS 8 November 2022 - now handled downstream
# edgelist.loc[(edgelist.relation_label == 'subClassOf'), 'relation_label'] = 'isa'
# edgelist['relation_label'] = edgelist['relation_label'].str.replace(' ', '_')

# Format subject node information.
# JAS string replacements moved to codeReplacements function.

# edgelist['subject'] = \
# edgelist['subject'].str.replace(':', ' ').str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]
edgelist['subject'] = parsetools.codeReplacements(edgelist['subject'],OWL_SAB)

# JAS 15 NOV 2022
# Deprecate all prior code that handled object nodes, including from October 2022, in favor of the
# improved codeReplacements function.
edgelist['object'] = parsetools.codeReplacements(edgelist['object'],OWL_SAB)

# ------------- DEPRECATED
# JAS 13 OCT 2022
# Format object node information.
# Enhancement to handle special case of HGNC object nodes.

# HGNC nodes are a special case.
# The codes are in the format "HGNC HGNC:ID", and thus correspond to two delimiters recognized by the
# general text processing/codeReplacements logic. However, the HGNC codes are stored in CUI-CODES in
# exactly this format, so processing them breaks the link.
# Instead of trying to game the general string formatting, simply assume that HGNC codes are properly
# formatted and do not convert them.

# In general, a set of object nodes can be a mixture of nodes from HGNC and other vocabularies.

# original code:
# edgelist['object'] = \
# edgelist['object'].str.replace(':', ' ').str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]
# edgelist['object'] = codeReplacements(edgelist['object'])

# new code:

# If the nodes are not from HGNC, replace delimiters with space.
# edgelist['object'] = np.where(edgelist['object'].str.contains('HGNC') == True, \
# edgelist['object'], \
# edgelist['object'].str.replace(':', ' ').str.replace('#', ' ').str.replace('_',
# ' ').str.split(
# '/').str[-1])
# If the nodes are not from HGNC, align code SABs with UMLS.
# edgelist['object'] = np.where(edgelist['object'].str.contains('HGNC') == True, \
# edgelist['object'], \
# codeReplacements(edgelist['object']))
# ------------- DEPRECATED


# #################################################
# JAS 8 NOV 2022
# Obtain descriptions of relationships and their inverses from Relations Ontology JSON.

# The Relations Ontology (RO) is an ontology of relationships, in which the nodes are
# relationship properties and the edges (predicates) are relationships *between*
# relationship properties.
# For example,
# relationship property RO_0002292 (node) inverseOf (edge) relationship property RO_0002206 (node)
# or
# "expresses" inverseOf "expressed in"

dfro = pd.read_json("https://raw.githubusercontent.com/oborel/obo-relations/master/ro.json")

# Information on relationship properties (i.e., relationship property nodes) is in the node array.
dfnodes = pd.DataFrame(dfro.graphs[0]['nodes'])
# Information on edges (i.e., relationships between relationship properties) is in the edges array.
dfedges = pd.DataFrame(dfro.graphs[0]['edges'])

# Information on the relationships between relationship properties *should be* in the edges array.
# Example of edge element:
# {
#      "sub" : "http://purl.obolibrary.org/obo/RO_0002101",
#      "pred" : "inverseOf",
#      "obj" : "http://purl.obolibrary.org/obo/RO_0002132"
#    }
#
# The ontology graph requires that every relationship have an inverse.
# Not all relationships in RO are defined with inverses, so the script will create
# "pseudo-inverse" relationships--e.g., if the only information available is the label "eats", then
# the pseudo-inverse will be "inverse_eats" (instead of, say, "eaten_by").

# Cases that require pseudo-inverses include:
# 1. A property is incompletely specified in terms of both sides of an inverse relationship--e.g.,
#    RO_0002206 is listed as the inverse of RO_0002292, but RO_0002292 is not listed as the
#    corresponding inverse of RO_0002206. For these properties, the available relationship
#    will be inverted when joining relationship information to the edgelist.
#    (This is really a case in which both directions of the inverse relationship should have been
#    defined in the edges node, but were not.)
# 2. A property does not have inverse relationships defined in RO.
#    The relationship will be added to the list with a null inverse. The script will later create a
#    pseudo-inverse by appending "inverse_" to the relationship label.

# ---------------------------------

# Obtain triple information for relationship properties--i.e.,
# 1. IRIs for "subject" nodes and "object" nodes (relationship properties)
# 2. relationship predicates (relationships between relationship properties)
# The assumption is that each relationship property node has at least one edge (predicate).

# (Possible enhancement: find relationship properties in RO that do not have an edge. This really
# would be shaking the RO tree pretty hard, though.)

# Get subject node, edge
dfrelationtriples = dfnodes.merge(dfedges, how='inner', left_on='id', right_on='sub')
# Get object node
dfrelationtriples = dfrelationtriples.merge(dfnodes, how='inner', left_on='obj', right_on='id')

# ---------------------------------
# Identify relationship properties that do not have inverses.
# 1. Group relationship properties by predicate, using count.
#    ('pred' here describes the relationship between relationship properties.)
dfpred = dfrelationtriples.groupby(['id_x', 'pred']).count().reset_index()

# 2. Identify the relationships for which the set of predicates does not include "inverseOf".
listinv = dfpred[dfpred['pred'] == 'inverseOf']['id_x'].to_list()
listnoinv = dfpred[~dfpred['id_x'].isin(listinv)]['id_x'].to_list()
dfnoinv = dfrelationtriples.copy()
dfnoinv = dfnoinv[dfnoinv['id_x'].isin(listnoinv)]

# 3. Rename column names to match the relationtriples frame. (Column names are described
#    farther down.)
dfnoinv = dfnoinv[['id_x', 'lbl_x', 'id_y', 'lbl_y']].rename(
    columns={'id_x': 'IRI', 'lbl_x': 'relation_label_RO', 'id_y': 'inverse_IRI', 'lbl_y': 'inverse_RO'})
# The inverses are undefined.
dfnoinv['inverse_IRI'] = np.nan
dfnoinv['inverse_RO'] = np.nan

# ---------------------------------
# Look for members of incomplete inverse pairs--i.e., relationship properties that are
# the *object* of an inverseOf edge, but not the corresponding *subject* of an inverseOf edge.
#
# 1. Filter edges to inverseOf.
dfedgeinv = dfedges[dfedges['pred'] == 'inverseOf']

# 2. Find all relation properties that are objects of inverseOf edges.
dfnoinv = dfnoinv.merge(dfedgeinv, how='left', left_on='IRI', right_on='obj')

# 3. Get the label for the relation properties that are subjects of inverseOf edges.
dfnoinv = dfnoinv.merge(dfnodes, how='left', left_on='sub', right_on='id')
dfnoinv['inverse_IRI'] = np.where(dfnoinv['lbl'].isnull(), dfnoinv['inverse_IRI'], dfnoinv['id'])
dfnoinv['inverse_RO'] = np.where(dfnoinv['lbl'].isnull(), dfnoinv['inverse_RO'], dfnoinv['lbl'])
dfnoinv = dfnoinv[['IRI', 'relation_label_RO', 'inverse_IRI', 'inverse_RO']]

# ---------------------------------
# Filter the base triples frame to just those relationship properties that have inverses.
# This step eliminates relationship properties related by relationships such as "subPropertyOf".
dfrelationtriples = dfrelationtriples[dfrelationtriples['pred'] == 'inverseOf']

# Rename column names.
# Column names will be:
# IRI - the IRI for the relationship property
# relation_label_RO - the label for the relationship property
# inverse_RO - the label of the inverse relationship property
# inverse_IRI - IRI for the inverse relationship (This will be dropped.)
dfrelationtriples = dfrelationtriples[['id_x', 'lbl_x', 'id_y', 'lbl_y']].rename(
    columns={'id_x': 'IRI', 'lbl_x': 'relation_label_RO', 'id_y': 'inverse_IRI', 'lbl_y': 'inverse_RO'})

# Add triples for problematic relationship properties--i.e., without inverses or from incomplete pairs.
dfrelationtriples = pd.concat([dfrelationtriples, dfnoinv], ignore_index=True).drop_duplicates(subset=['IRI'])

# Convert stings for labels for relationships to expected delimiting.
dfrelationtriples['relation_label_RO'] = \
    dfrelationtriples['relation_label_RO'].str.replace(' ', '_').str.split('/').str[-1]
dfrelationtriples['inverse_RO'] = dfrelationtriples['inverse_RO'].str.replace(' ', '_').str.split('/').str[-1]

dfrelationtriples = dfrelationtriples.drop(columns='inverse_IRI')

# #################################################
# JAS 8 NOV 2022
# JOIN RELATIONS WITH EDGES
# Rewrite of join logic to account for:
# 1. Optional use of OWLNETS_relations.txt file.
# 2. Identification of all relations in Relations Ontology, not just inverses.

# Perform a series of joins and rename resulting columns to keep track of the source of
# relationship labels and inverse relationship labels.

# Check for relationships in RO, considering the edgelist predicate as a *full IRI*.
edgelist = edgelist.merge(dfrelationtriples, how='left', left_on='predicate',
                          right_on='IRI').drop_duplicates().reset_index(drop=True)
# JAS 6 JAN 2023 add optional evidence_class
edgelist = edgelist[
    ['subject', 'predicate', 'object', 'evidence_class', 'relation_label_from_file', 'relation_label_RO',
     'inverse_RO']].rename(
    columns={'relation_label_RO': 'relation_label_RO_fromIRIjoin', 'inverse_RO': 'inverse_RO_fromIRIjoin'})

# Check for relationships in RO by label, considering the edgelist predicate as *a label*--e.g.,
# as a simplified version of an IRI.
# First, format the predicate string to match potential relationship strings from RO.
# Parsing note: relationship IRIs often include the '#' character as a terminal delimiter, and
# be in format url...#relation--e.g., ccf.owl#ct_is_a.
edgelist['predicate'] = edgelist['predicate'].str.replace(' ', '_').str.replace('#', '/').str.split('/').str[-1]
edgelist = edgelist.merge(dfrelationtriples, how='left', left_on='predicate',
                          right_on='relation_label_RO').drop_duplicates().reset_index(drop=True)

# JAS 6 JAN 2023 add optional evidence_class
edgelist = edgelist[
    ['subject', 'predicate', 'object', 'evidence_class', 'relation_label_from_file', 'relation_label_RO_fromIRIjoin',
     'inverse_RO_fromIRIjoin', 'relation_label_RO', 'inverse_RO']].rename(
    columns={'relation_label_RO': 'relation_label_RO_frompredicatejoinlabel',
             'inverse_RO': 'inverse_RO_frompredicatejoinlabel'})

# Check for relationships in RO by label, considering the relationship label from the
# OWLNETS_relations.txt file that corresponds to the predicate (if available).
if relations_file_exists:
    edgelist['relation_label_from_file'] = \
        edgelist['relation_label_from_file'].str.replace(' ', '_').str.replace('#', '/').str.split('/').str[-1]
    edgelist = edgelist.merge(dfrelationtriples, how='left', left_on='relation_label_from_file',
                              right_on='relation_label_RO').drop_duplicates().reset_index(drop=True)
    # JAS 6 JAN 2023 add optional evidence_class
    edgelist = edgelist[['subject', 'predicate', 'object', 'evidence_class', 'relation_label_from_file',
                         'relation_label_RO_fromIRIjoin',
                         'inverse_RO_fromIRIjoin', 'relation_label_RO_frompredicatejoinlabel',
                         'inverse_RO_frompredicatejoinlabel', 'relation_label_RO', 'inverse_RO']].rename(
        columns={'relation_label_RO': 'relation_label_RO_fromfilelabeljoinlabel',
                 'inverse_RO': 'inverse_RO_fromfilelabeljoinlabel'})

# We now have labels for relations and inverses for the following scenarios:
# 1. relation_label_RO_fromIRIjoin/inverse_fromIRIjoin - predicate was a full IRI that was in RO
# 2. relation_label_RO_fromlabeljoin/inverse_fromlabeljoin - predicate corresponds to the label
#    of a relation property in RO
# 3. relation_label_from_file/(null inverse) - relation label from the OWLNETS_relations.txt.
#    The label is either the label of a relationship with IRI not in RO or a custom relationship label.
# 4. predicate/(null inverse) - a custom relationship label

# Order of precedence for relationship/inverse relationship data:
# 1. label from the edgelist predicate joined to RO by IRI
# 2. label from the edgelist predicate joined to RO by label
# 3. label from OWLNETS_relations.txt, joined against RO
# 4. label from OWLNETS_relations.txt, not joined against RO
# 5. predicate from edgelist
# 6. 'subClassOf' predicates converted to 'isa'
# 7. JAS 13 JAN 2023 - 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type' converted to 'isa'

edgelist['relation_label'] = edgelist['relation_label_RO_fromIRIjoin']
edgelist['relation_label'] = np.where(edgelist['relation_label'].isnull(),
                                      edgelist['relation_label_RO_frompredicatejoinlabel'], edgelist['relation_label'])
if relations_file_exists:
    edgelist['relation_label'] = np.where(edgelist['relation_label'].isnull(),
                                          edgelist['relation_label_RO_fromfilelabeljoinlabel'],
                                          edgelist['relation_label'])
    edgelist['relation_label'] = np.where(edgelist['relation_label'].isnull(), edgelist['relation_label_from_file'],
                                          edgelist['relation_label'])
edgelist['relation_label'] = np.where(edgelist['relation_label'].isnull(), edgelist['predicate'],
                                      edgelist['relation_label'])
edgelist['relation_label'] = np.where(edgelist['predicate'].str.contains('subClassOf'), 'isa',
                                      edgelist['relation_label'])

# JAS 13 JAN 2023 - 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type' converted to 'isa'
edgelist['relation_label'] = np.where(edgelist['predicate'].str.contains('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), 'isa',
                                      edgelist['relation_label'])
# The algorithm for inverses is simpler: if one was derived from RO, use it; else leave empty, and
# the script will create a pseudo-inverse.
edgelist['inverse'] = edgelist['inverse_RO_fromIRIjoin']
edgelist['inverse'] = np.where(edgelist['inverse'].isnull(), edgelist['inverse_RO_frompredicatejoinlabel'],
                               edgelist['inverse'])
if relations_file_exists:
    edgelist['inverse'] = np.where(edgelist['inverse'].isnull(), edgelist['inverse_RO_fromfilelabeljoinlabel'],
                                   edgelist['inverse'])

# In[9]:

# JAS 8 NOV 2022 -
# Original code that assumed that joins were only to inverse relations.
# edgelist = edgelist.merge(df, how='left', left_on='relation_label', right_on='lbl').drop_duplicates().reset_index(
# drop=True)
# edgelist.drop(columns=['lbl'], inplace=True)
# del df

# #### Add unknown inverse_ edges (i.e., pseudo-inverses)

# In[10]:

edgelist.loc[edgelist['inverse'].isnull(), 'inverse'] = 'inverse_' + edgelist['relation_label']

# ### Clean up node_metadata

# In[11]:

print('Cleaning up node metadata...')

# CodeID
# CodeID
# JAS 15 November string replacements moved to codeReplacements function.
# node_metadata['node_id'] = \
# node_metadata['node_id'].str.replace(':', ' ').str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]
node_metadata['node_id'] = parsetools.codeReplacements(node_metadata['node_id'],OWL_SAB)

# synonyms .loc of notna to control for owl with no syns
node_metadata.loc[node_metadata['node_synonyms'].notna(), 'node_synonyms'] = \
    node_metadata[node_metadata['node_synonyms'].notna()]['node_synonyms'].astype('str').str.split('|')

# dbxref .loc of notna to control for owl with no dbxref
# 5 OCT 2022 - JAS: notice the conversion to uppercase. This requires a corresponding
#                   conversion when merging with CUI-CODEs data.
node_metadata.loc[node_metadata['node_dbxrefs'].notna(), 'node_dbxrefs'] = \
    node_metadata[node_metadata['node_dbxrefs'].notna()]['node_dbxrefs'].astype('str').str.upper().str.replace(':', ' ')
node_metadata['node_dbxrefs'] = node_metadata['node_dbxrefs'].str.split('|')
explode_dbxrefs = node_metadata.explode('node_dbxrefs')[['node_id', 'node_dbxrefs']].dropna().astype(
    str).drop_duplicates().reset_index(drop=True)
explode_dbxrefs['node_dbxrefs'] = parsetools.codeReplacements(explode_dbxrefs['node_dbxrefs'],OWL_SAB)

# Add SAB and CODE columns
# JAS 12 JAN 2023 - force uppercase for SAB
node_metadata['SAB'] = node_metadata['node_id'].str.split(' ').str[0].str.upper()
node_metadata['CODE'] = node_metadata['node_id'].str.split(' ').str[-1]
#del node_metadata['node_namespace']
# del explode_dbxrefs - not deleted here because we need it later


# ### Get the UMLS CUIs for each node_id as nodeCUIs

# In[12]:
print('ASSIGNING CUIs TO NODES, including for nodes that are cross-references...')

explode_dbxrefs['nodeXrefCodes'] = explode_dbxrefs['node_dbxrefs'].str.split(' ').str[-1]

# JAS JAN 2023 - added group_keys=False to silence the FutureWarning from Pandas.
explode_dbxrefs_UMLS = \
    explode_dbxrefs[explode_dbxrefs['node_dbxrefs'].str.contains('UMLS C') == True].groupby('node_id', sort=False, group_keys=False)[
        'nodeXrefCodes'].apply(list).reset_index(name='nodeCUIs')
node_metadata = node_metadata.merge(explode_dbxrefs_UMLS, how='left', on='node_id')
del explode_dbxrefs_UMLS
del explode_dbxrefs['nodeXrefCodes']

# ### Get the UMLS CUIs for each node_id from CUI-CODEs file as CUI_CODEs

# In[13]:

print('--reading CUI-CODES.csv...')
CUI_CODEs = pd.read_csv(csv_path("CUI-CODEs.csv"))
CUI_CODEs = CUI_CODEs.dropna().drop_duplicates().reset_index(drop=True)

# #### A big groupby - ran a couple minutes - changed groupby to not sort the keys to speed it up

# JAS 5 OCT 2022
# Enhancement to force case insensitivity of checking cross-referenced concepts.

# In general, the code for a concept in an ontology can be *mixed case*. Examples include:
# 1. EDAM: operation_00004
# 2. HUSAT: SampleMedia
# An earlier step in the script converts the codes to uppercase in node_metadata.
# Later merges with node_metadata on node_id requires that the right side also be uppercase.
# Without this conversion, dbxrefs for which the code is mixed case will be ignored, because they still
# exist in mixed case in CUI_CODEs.csv.

# In[14]:

print('--flattening data from CUI_CODEs...')
CODE_CUIs = CUI_CODEs.groupby(':END_ID', sort=False)[':START_ID'].apply(list).reset_index(name='CUI_CODEs')
# JAS the call to upper is new.
print('--merging data from CUI_CODEs to node metadata...')
node_metadata = node_metadata.merge(CODE_CUIs, how='left', left_on='node_id', right_on=CODE_CUIs[':END_ID'].str.upper())
del CODE_CUIs
del node_metadata[':END_ID']

# ### Add column for Xref's CUIs - merge exploded_node_metadata with CUI_CODEs then group, eliminate duplicates and merge with node_metadata

# In[15]:

# JAS 5 OCT 2022
# In general, the code for a concept in an ontology can be mixed case. Examples include:
# 1. EDAM: operation_00004
# 2. HUSAT: SampleMedia
# An earlier step converts the codes to uppercase in node_metadata, so later merges with node_metadata
# on node_id requires that the right side also be uppercase. Without this conversion, dbxrefs
# for which the code is mixed case will be ignored.

# Original code
# node_xref_cui = explode_dbxrefs.merge(CUI_CODEs, how='inner', left_on='node_dbxrefs', right_on=':END_ID')
# New code uses upper.
node_xref_cui = explode_dbxrefs.merge(CUI_CODEs, how='inner', left_on='node_dbxrefs',
                                      right_on=CUI_CODEs[':END_ID'].str.upper())
# JAS FEB 2023 Adding group_keys=False to silence the FutureWarning.
node_xref_cui = node_xref_cui.groupby('node_id', sort=False,group_keys=False)[':START_ID'].apply(list).reset_index(name='XrefCUIs')
node_xref_cui['XrefCUIs'] = node_xref_cui['XrefCUIs'].apply(lambda x: pd.unique(x)).apply(list)
node_metadata = node_metadata.merge(node_xref_cui, how='left', on='node_id')
del node_xref_cui
del explode_dbxrefs


# ### Add column for base64 CUIs

# In[16]:


def base64it(x):
    return [base64.urlsafe_b64encode(str(x).encode('UTF-8')).decode('ascii')]


node_metadata['base64cui'] = node_metadata['node_id'].apply(base64it)

# ### Add cuis list and preferred cui to complete the node "atoms" (code, label, syns, xrefs, cuis, CUI)

# In[17]:

print('--assigning CUIs to nodes...')
# create correct length lists
node_metadata['cuis'] = node_metadata['base64cui']
node_metadata['CUI'] = ''

# join list across row
node_metadata['cuis'] = node_metadata[['nodeCUIs', 'CUI_CODEs', 'XrefCUIs', 'base64cui']].values.tolist()

# remove nan, flatten, and remove duplicates - retains order of elements which is key to consistency
node_metadata['cuis'] = node_metadata['cuis'].apply(lambda x: [i for i in x if i == i])
node_metadata['cuis'] = node_metadata['cuis'].apply(lambda x: [i for row in x for i in row])
node_metadata['cuis'] = node_metadata['cuis'].apply(lambda x: pd.unique(x)).apply(list)

# iterate to select one CUI from cuis in row order - we ensure each node_id has its own distinct CUI
# each node_id is assigned one CUI distinct from all others' CUIs to ensure no self-reference in edgelist
node_idCUIs = []
nmCUI = []
for index, rows in node_metadata.iterrows():
    addedone = False
    for x in rows.cuis:
        if ((x in node_idCUIs) | (addedone == True)):
            dummy = 0
        else:
            nmCUI.append(x)
            node_idCUIs.append(x)
            addedone = True
    # JAS 17 oct 2022
    # For the edge case in which multiple nodes have the same cross-reference AND the
    # cross-reference maps to a single CUI (the case for around 20 nodes in MP--e.g., all
    # those that share CL 0000959 as a cross-reference), only one of the nodes will be
    # assigned the CUI of the cross-reference. The rest of the nodes will lose the
    # cross-reference.
    # The following block keeps the nmCUI list the same size as node_metadata['CUI'].
    if addedone == False:
        nmCUI.append('')
        node_idCUIs.append('')

node_metadata['CUI'] = nmCUI

# ### Join CUI from node_metadata to each edgelist subject and object

# #### Assemble CUI-CUIs
print('Assembling CUI-CUI relationships...')
# In[18]:
# Merge subject and object nodes with their CUIs; drop the codes; and add the SAB.

# The product will be a DataFrame in the format
# CUI1 relation CUI2 inverse
# e.g.,
# CUI1 isa CUI2 inverse_isa

# JAS 20 OCT 2022 Trim objnode1 and objnode2 DataFrames to reduce memory demand. (This is an issue for large
# ontologies, such as PR.)
if OWL_SAB == 'PR':
    # The node_metadata DataFrame has been filtered to proteins from a specified organism.
    # The edgelist DataFrame also needs to be filtered via merging.
    mergehow = 'inner'
else:
    # The node_metadata has not been filtered.
    mergehow = 'left'

# Assign CUIs to subject nodes.
edgelist = edgelist.merge(node_metadata, how=mergehow, left_on='subject', right_on='node_id')
# JAS 6 JANUARY 2023 - add evidence_class
edgelist = edgelist[['CUI', 'relation_label', 'object', 'inverse', 'evidence_class']]
edgelist.columns = ['CUI1', 'relation_label', 'object', 'inverse', 'evidence_class']

# Assign CUIs to object nodes.

# Original code for object node CUIs
# edgelist = edgelist.merge(node_metadata, how='left', left_on='object', right_on='node_id')
# edgelist = edgelist[['CUI1','relation_label','CUI','inverse']]
# edgelist.columns = ['CUI1','relation_label','CUI2','inverse']

# JAS 11 OCT 2022
# Enhancement to allow for case of object nodes in relationships that are external to the ontology. The
# initial use case is the mapping of UNIPROTKB proteins to genes in HGNC.

# Object nodes can be one of two types:
# 1. Object nodes that are also subject nodes, and thus in node_metadata. This is usually the case for subjects
#    and objects that are from the same ontology. The codes and CUIs for these are properly formatted for the
#    ontology as a consequence of this script.
# 2. Object nodes that are not subject nodes in node_metadata, but may be in the CUI-CODEs data.
#    This is the case for ontologies for which nodes have relations with nodes in other ontologies that
#    are not isa (subClassOf) or dbxref (equivalence classes)--e.g., UNIPROTKB, in which
#    concepts from UNIPROTKB have "gene product of" relationships to HGNC concepts.
#    Because the object nodes are not in node_metada, it is assumed that the codes and CUIs for object nodes
#    conform to their representation in CUI-CODEs.

# It is, in theory, possible that an ontology's object nodes would be of a combination of internal and external
# concepts--i.e., that some object nodes are defined in node_metadata and others in CUI-CODEs. It is necessary
# to check both possibilities for each subject node in the edge list.

# Check first for object nodes in node_metadata--i.e., of type 1.
# Matching CUIs will be in a field named 'CUI'.
# JAS 6 JANUARY 2023 - add evidence_class
objnode1 = edgelist.merge(node_metadata, how=mergehow, left_on='object', right_on='node_id')
objnode1 = objnode1[['object', 'CUI1', 'relation_label', 'inverse', 'CUI', 'evidence_class']]

# Check for object nodes in CUI_CODEs--i.e., of type 2. Matching CUIs will be in a field named ':END_ID'.
objnode2 = edgelist.merge(CUI_CODEs, how=mergehow, left_on='object', right_on=':END_ID')
# JAS 6 JANUARY 2023 - add evidence_class
objnode2 = objnode2[['object', 'CUI1', 'relation_label', 'inverse', ':START_ID', 'evidence_class']]

# Union (pd.concat with drop_duplicates) objNode1 and objNode2 to allow for conditional
# selection of CUI.
# The union will result in a DataFrame with columns for each node:
# object CUI1 relation_label inverse CUI :START_ID

objnode = pd.concat([objnode1, objnode2]).drop_duplicates()

# If CUI is non-null, then the node is of the first type; otherwise, it is likely of the second type.
objnode['CUIMatch'] = objnode[':START_ID'].where(objnode['CUI'].isna(), objnode['CUI'])

# original code
# edgelist = edgelist.merge(node_metadata, how='left', left_on='object', right_on='node_id')

# JAS 6 JANUARY 2023 - add evidence_class
edgelist = objnode[['CUI1', 'relation_label', 'CUIMatch', 'inverse', 'evidence_class']]

# Merge object nodes with subject nodes.

# original code
# edgelist = edgelist.dropna().drop_duplicates().reset_index(drop=True)
# edgelist = edgelist[['CUI1','relation_label','CUI','inverse']]

# JAS 6 JANUARY 2023 - Add evidence_class
edgelist.columns = ['CUI1', 'relation_label', 'CUI2', 'inverse', 'evidence_class']
# JAS 6 JANUARY 2023 - subset to account for optional evidence_class
subset = ['CUI1', 'relation_label', 'CUI2', 'inverse']
edgelist = edgelist.dropna(subset=subset).drop_duplicates(subset=subset).reset_index(drop=True)

edgelist['SAB'] = OWL_SAB

# ## Write out files

# ### Test existence when appropriate in original csvs and then add data for each csv

# #### Write CUI-CUIs (':START_ID', ':END_ID', ':TYPE', 'SAB', 'evidence_class') (no prior-existence-check because want them in this SAB)

# In[19]:
print('Appending to CUI-CUIs.csv...')

# TWO WRITES comment out during development

# JAS 6 JAN 2023 Add evidence_class column to file.
print('Adding evidence_class column to CUI-CUIs.csv...')
fcsv = csv_path('CUI-CUIs.csv')
# evidence_class should be a number.
new_header_columns = [':START_ID', ':END_ID', ':TYPE,SAB', 'evidence_class:float']
update_columns_to_csv_header(fcsv, new_header_columns)

# forward ones
# JAS 6 JAN 2023 Add evidence_class. (The SAB column was added after evidence_class above.)
edgelist.columns = [':START_ID', ':TYPE', ':END_ID', 'inverse', 'evidence_class', 'SAB']
edgelist[[':START_ID', ':END_ID', ':TYPE', 'SAB', 'evidence_class']].to_csv(csv_path('CUI-CUIs.csv'), mode='a',
                                                                            header=False, index=False)

# reverse ones
# JAS 6 JAN 2023 Add evidence_class. (The SAB column was added after evidence_class above.)
edgelist.columns = [':END_ID', 'relation_label', ':START_ID', ':TYPE', 'evidence_class', 'SAB']
edgelist[[':START_ID', ':END_ID', ':TYPE', 'SAB', 'evidence_class']].to_csv(csv_path('CUI-CUIs.csv'), mode='a',
                                                                            header=False, index=False)
del edgelist

# #### Write CODEs (CodeID:ID,SAB,CODE,value,lowerbound,upperbound,unit) - with existence check against CUI-CODE.csv

# In[20]:

print('Appending to CODEs.csv...')

# JAS 6 JAN 2023 Add value, lowerbound, upperbound, unit column to file.
print('Adding value, lowerbound, upperbound, unit columns to CODES.csv...')
fcsv = csv_path('CODEs.csv')
# value, lowerbound, and upperbound should be numbers.
new_header_columns = ['CodeID:ID', 'SAB', 'CODE', 'value:float', 'lowerbound:float', 'upperbound:float', 'unit']
update_columns_to_csv_header(fcsv, new_header_columns)

# JAS 6 JAN 2023 add value, lowerbound, upperbound, unit
newCODEs = node_metadata[['node_id', 'SAB', 'CODE', 'CUI_CODEs', 'value', 'lowerbound', 'upperbound', 'unit']]
newCODEs = newCODEs[newCODEs['CUI_CODEs'].isnull()]
newCODEs = newCODEs.drop(columns=['CUI_CODEs'])
newCODEs = newCODEs.rename({'node_id': 'CodeID:ID'}, axis=1)

# JAS 6 JAN 2023 add subset to ignore optional columns. Add fillna to remove NaNs from optional columns.
subset = subset = ['CodeID:ID', 'SAB', 'CODE']
newCODEs = newCODEs.dropna(subset=subset).drop_duplicates(subset=subset).reset_index(drop=True).fillna('')
# write/append - comment out during development
newCODEs.to_csv(csv_path('CODEs.csv'), mode='a', header=False, index=False)

del newCODEs

# #### Write CUIs (CUI:ID) - with existence check against CUI-CODE.csv

# In[21]:

print('Appending to CUIs.csv...')
CUIs = CUI_CODEs[[':START_ID']].dropna().drop_duplicates().reset_index(drop=True)
CUIs.columns = ['CUI:ID']

newCUIs = node_metadata[['CUI']]
newCUIs.columns = ['CUI:ID']

# Here we isolate only the rows not already matching in existing files
df = newCUIs.drop_duplicates().merge(CUIs.drop_duplicates(), on=CUIs.columns.to_list(), how='left', indicator=True)
newCUIs = df.loc[df._merge == 'left_only', df.columns != '_merge']
newCUIs.reset_index(drop=True, inplace=True)

newCUIs = newCUIs.dropna().drop_duplicates().reset_index(drop=True)
# write/append - comment out during development
newCUIs.to_csv(csv_path('CUIs.csv'), mode='a', header=False, index=False)

# del newCUIs - do not delete here because we need newCUIs list later
# del CUIs


# #### Write CUI-CODEs (:START_ID,:END_ID) - with existence check against CUI-CODE.csv

# In[22]:
print('Appending to CUI_CODES.csv...')

# The last CUI in cuis is always base64 of node_id - here we grab those only if they are the selected CUI (and all CUIs)
newCUI_CODEsCUI = node_metadata[['CUI', 'node_id']]
newCUI_CODEsCUI.columns = [':START_ID', ':END_ID']

# Here we grab all the rest of the cuis except for last in list (excluding single-length cuis lists first)
newCUI_CODEscuis = node_metadata[['cuis', 'node_id']][node_metadata['cuis'].apply(len) > 1]
newCUI_CODEscuis['cuis'] = newCUI_CODEscuis['cuis'].apply(lambda x: x[:-1])
newCUI_CODEscuis = newCUI_CODEscuis.explode('cuis')[['cuis', 'node_id']]
newCUI_CODEscuis.columns = [':START_ID', ':END_ID']

newCUI_CODEs = pd.concat([newCUI_CODEsCUI, newCUI_CODEscuis], axis=0).dropna().drop_duplicates().reset_index(drop=True)

# Here we isolate only the rows not already matching in existing files
df = newCUI_CODEs.merge(CUI_CODEs, on=CUI_CODEs.columns.to_list(), how='left', indicator=True)
newCUI_CODEs = df.loc[df._merge == 'left_only', df.columns != '_merge']
newCUI_CODEs = newCUI_CODEs.dropna().drop_duplicates().reset_index(drop=True)

# write/append - comment out during development
newCUI_CODEs.to_csv(csv_path('CUI-CODEs.csv'), mode='a', header=False, index=False)

del newCUI_CODEsCUI
del newCUI_CODEscuis
del df
del newCUI_CODEs

# #### Load SUIs from csv

# In[23]:

SUIs = pd.read_csv(csv_path("SUIs.csv"))
# SUIs supposedly unique but...discovered 5 NaN names in SUIs.csv and drop them here
# ?? from ASCII converstion for Oracle to Pandas conversion on original UMLS-Graph-Extracts ??
SUIs = SUIs.dropna().drop_duplicates().reset_index(drop=True)

# #### Write SUIs (SUI:ID,name) part 1, from label - with existence check

# In[24]:
print('Appending to SUIs.csv...')

newSUIs = node_metadata.merge(SUIs, how='left', left_on='node_label', right_on='name')[
    ['node_id', 'node_label', 'CUI', 'SUI:ID', 'name']]

# for Term.name that don't join with node_label update the SUI:ID with base64 of node_label
newSUIs.loc[(newSUIs['name'] != newSUIs['node_label']), 'SUI:ID'] = \
    newSUIs[newSUIs['name'] != newSUIs['node_label']]['node_label'].apply(base64it).str[0]

# change field names and isolate non-matched ones (don't exist in SUIs file)
newSUIs.columns = ['node_id', 'name', 'CUI', 'SUI:ID', 'OLDname']
newSUIs = newSUIs[newSUIs['OLDname'].isnull()][['node_id', 'name', 'CUI', 'SUI:ID']]
newSUIs = newSUIs.dropna().drop_duplicates().reset_index(drop=True)
newSUIs = newSUIs[['SUI:ID', 'name']]

# update the SUIs dataframe to total those that will be in SUIs.csv
SUIs = pd.concat([SUIs, newSUIs], axis=0).reset_index(drop=True)

# write out newSUIs - comment out during development
newSUIs.to_csv(csv_path('SUIs.csv'), mode='a', header=False, index=False)

# del newSUIs - not here because we use this dataframe name later


# #### Write CUI-SUIs (:START_ID,:END_ID)
print('Appending to CUI-SUIs.csv...')
# In[25]:

# get the newCUIs associated metadata (CUIs are unique in node_metadata)
newCUI_SUIs = newCUIs.merge(node_metadata, how='inner', left_on='CUI:ID', right_on='CUI')
newCUI_SUIs = newCUI_SUIs[['node_label', 'CUI']].dropna().drop_duplicates().reset_index(drop=True)

# get the SUIs matches
newCUI_SUIs = newCUI_SUIs.merge(SUIs, how='left', left_on='node_label', right_on='name')[
    ['CUI', 'SUI:ID']].dropna().drop_duplicates().reset_index(drop=True)
newCUI_SUIs.columns = [':START:ID', ':END_ID']

# write/append - comment out during development
newCUI_SUIs.to_csv(csv_path('CUI-SUIs.csv'), mode='a', header=False, index=False)

# del newCUIs
# del newCUI_SUIs


# #### Load CODE-SUIs and reduce to PT or SY

# In[26]:

print('Appending to CODE-SUIs.csv...')

CODE_SUIs = pd.read_csv(csv_path("CODE-SUIs.csv"))
CODE_SUIs = CODE_SUIs[((CODE_SUIs[':TYPE'] == 'PT') | (CODE_SUIs[':TYPE'] == 'SY'))]
CODE_SUIs = CODE_SUIs.dropna().drop_duplicates().reset_index(drop=True)

# #### Write CODE-SUIs (:END_ID,:START_ID,:TYPE,CUI) part 1, from label - with existence check

# In[27]:


# JAS MARCH 2023 - change to address issue #42.

# JCS original comment:
# This does NOT (yet) address two different owl files asserting two different SUIs as PT with the same CUI,CodeID
# by choosing the first one in the build process (by comparing only three columns in the existence check)
# - a Code/CUI would thus have only one PT relationship (to only one SUI) so that is not guaranteed right now
# (its good practice in query to deduplicate anyway results - because for example even fully addressed
# two PT relationships could exist between a CODE and SUI if they are asserted on different CUIs) -
# to assert a vocabulary-specific relationship type as vocabulary-specific preferred term (an ingest parameter perhaps)
# one would create a PT (if it doesn't have one) and a SAB_PT - that is the solution for an SAB that wants
# to assert PT on someone else's Code (CCF may want this so there could be CCF_PT Terms on UBERON codes) -
# note that for SY later, this is not an issue because SY are expected to be multiple and so we use all
# four columns in the existence check there too but intend to keep that one that way.

# JAS March 2023
# Assign terms for codes of nodes indicated in the nodes file:
#   If the SAB for the assertion set/ontology is the same as the SAB for the code, then PT
#   else <SAB>_PT
# get the SUIs matches for SUIs
newCODE_SUIs = node_metadata.merge(SUIs, how='left', left_on='node_label', right_on='name')[['SUI:ID', 'node_id', 'CUI']].dropna().drop_duplicates().reset_index(drop=True)

newCODE_SUIs.insert(2, ':TYPE', 'PT')

# Change: if a term is being associated with a code by an ontology/set of assertions, it should be a PT only
# if the code belongs to the ontology; otherwise, the term should be a "SAB PT".
# For example, suppose that the following order of ingestion occurs:
# PATO, MP, UBERON
# The MP ontology uses codes from PATO, UBERON, and MP.

# 1. MP codes will have a PT term.
# 2. PATO codes will have terms with the following relationships:
#    a. PT - from the ingestion of PATO
#    b. MP_PT - from the ingestion of MP
# 3. UBERON codes will have terms with the following relationships:
#    a. PT - from the ingestion of UBERON
#    b. PATO_PT - from the ingestion of PATO
#    c. MP_PT - from the ingestion of MP

# If terms for codes are different in the different ontologies (e.g. MP, UBERON, and PATO used different terms to
# describe the same UBERON code, then there would be multiple terms. If, however, all ontologies use the same term,
# there would be just one term, but with multiple relationships.

newCODE_SUIs[':TYPE'] = np.where((OWL_SAB == newCODE_SUIs['node_id'].str.upper().str.split(' ').str[0]),'PT',OWL_SAB+'_PT')

newCODE_SUIs.columns = [':END_ID', ':START_ID', ':TYPE', 'CUI']

# Here we isolate only the rows not already matching in existing files
df = newCODE_SUIs.drop_duplicates().merge(CODE_SUIs.drop_duplicates(), on=CODE_SUIs.columns.to_list(), how='left',
                                          indicator=True)
newCODE_SUIs = df.loc[df._merge == 'left_only', df.columns != '_merge']
newCODE_SUIs.reset_index(drop=True, inplace=True)

# write out newCODE_SUIs - comment out during development
newCODE_SUIs.to_csv(csv_path('CODE-SUIs.csv'), mode='a', header=False, index=False)

# del newCODE_SUIs - will use this variable again later (though its overwrite)


# #### Write SUIs (SUI:ID,name) part 2, from synonyms - with existence check

# In[28]:


# explode and merge the synonyms
explode_syns = node_metadata.explode('node_synonyms')[
    ['node_id', 'node_synonyms', 'CUI']].dropna().drop_duplicates().reset_index(drop=True)
newSUIs = explode_syns.merge(SUIs, how='left', left_on='node_synonyms', right_on='name')[
    ['node_id', 'node_synonyms', 'CUI', 'SUI:ID', 'name']]

# for Term.name that don't join with node_synonyms update the SUI:ID with base64 of node_synonyms
newSUIs.loc[(newSUIs['name'] != newSUIs['node_synonyms']), 'SUI:ID'] = \
    newSUIs[newSUIs['name'] != newSUIs['node_synonyms']]['node_synonyms'].apply(base64it).str[0]

# change field names and isolate non-matched ones (don't exist in SUIs file)
newSUIs.columns = ['node_id', 'name', 'CUI', 'SUI:ID', 'OLDname']
newSUIs = newSUIs[newSUIs['OLDname'].isnull()][['node_id', 'name', 'CUI', 'SUI:ID']]
newSUIs = newSUIs.dropna().drop_duplicates().reset_index(drop=True)
newSUIs = newSUIs[['SUI:ID', 'name']]

# update the SUIs dataframe to total those that will be in SUIs.csv
SUIs = pd.concat([SUIs, newSUIs], axis=0).reset_index(drop=True)

# write out newSUIs - comment out during development
newSUIs.to_csv(csv_path('SUIs.csv'), mode='a', header=False, index=False)

del newSUIs
# del explode_syns


# #### Write CODE-SUIs (:END_ID,:START_ID,:TYPE,CUI) part 2, from synonyms - with existence check

# In[29]:


# get the SUIs matches
newCODE_SUIs = explode_syns.merge(SUIs, how='left', left_on='node_synonyms', right_on='name')[
    ['SUI:ID', 'node_id', 'CUI']].dropna().drop_duplicates().reset_index(drop=True)
newCODE_SUIs.insert(2, ':TYPE', 'SY')
newCODE_SUIs.columns = [':END_ID', ':START_ID', ':TYPE', 'CUI']

# Compare the new and old retaining only new
df = newCODE_SUIs.drop_duplicates().merge(CODE_SUIs.drop_duplicates(), on=CODE_SUIs.columns.to_list(), how='left',
                                          indicator=True)
newCODE_SUIs = df.loc[df._merge == 'left_only', df.columns != '_merge']
newCODE_SUIs.reset_index(drop=True, inplace=True)

# write out newCODE_SUIs - comment out during development
newCODE_SUIs.to_csv(csv_path('CODE-SUIs.csv'), mode='a', header=False, index=False)

del newCODE_SUIs

# #### Write DEFs (ATUI:ID, SAB, DEF) and DEFrel (:END_ID, :START_ID) - with check for any DEFs and existence check

# In[30]:
print('Appending to DEFs.csv and DEFrel.csv...')

if node_metadata['node_definition'].notna().values.any():
    DEFs = pd.read_csv(csv_path("DEFs.csv"))
    DEFrel = pd.read_csv(csv_path("DEFrel.csv")).rename(columns={':START_ID': 'CUI', ':END_ID': 'ATUI:ID'})
    DEF_REL = DEFs.merge(DEFrel, how='inner', on='ATUI:ID')[
        ['SAB', 'DEF', 'CUI']].dropna().drop_duplicates().reset_index(drop=True)
    newDEF_REL = node_metadata[['SAB', 'node_definition', 'CUI']].rename(columns={'node_definition': 'DEF'})

    # Compare the new and old retaining only new
    df = newDEF_REL.drop_duplicates().merge(DEF_REL.drop_duplicates(), on=DEF_REL.columns.to_list(), how='left',
                                            indicator=True)
    newDEF_REL = df.loc[df._merge == 'left_only', df.columns != '_merge']
    newDEF_REL.reset_index(drop=True, inplace=True)

    # Add identifier
    newDEF_REL['ATUI:ID'] = newDEF_REL['SAB'] + " " + newDEF_REL['DEF'] + " " + newDEF_REL['CUI']
    newDEF_REL['ATUI:ID'] = newDEF_REL['ATUI:ID'].apply(base64it).str[0]
    newDEF_REL = newDEF_REL[['ATUI:ID', 'SAB', 'DEF', 'CUI']].dropna().drop_duplicates().reset_index(drop=True)

    # Write newDEFs
    newDEF_REL[['ATUI:ID', 'SAB', 'DEF']].to_csv(csv_path('DEFs.csv'), mode='a', header=False, index=False)

    # Write newDEFrel
    newDEF_REL[['ATUI:ID', 'CUI']].rename(columns={'ATUI:ID': ':END_ID', 'CUI': ':START_ID'}).to_csv(
        csv_path('DEFrel.csv'), mode='a', header=False, index=False)

    del DEFs
    del DEFrel
    del DEF_REL
    del newDEF_REL
