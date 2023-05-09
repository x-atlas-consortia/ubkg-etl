#!/usr/bin/env python
# coding: utf-8
import numpy as np
import pandas as pd
import os

# UBKG utilities for parsing

# codeReplacements - shared by at least the following scripts:
# OWLNETS-UMLS-GRAPH
# skowlnets

def getPrefixes()->pd.DataFrame:
    # Reads a resource file of SAB/prefixes.

    prefixfile = 'prefixes.csv'
    df = pd.DataFrame()

    if os.path.exists(prefixfile):
        df= pd.read_csv(prefixfile)
    return df

def codeReplacements(x:pd.Series, ingestSAB: str):

    # This function converts strings that correspond to either codes or CUIs for concepts to a format
    # recognized by the knowledge graph.


    # Arguments:
    #  x - Pandas Series object containing information on either:
    #      a node (subject or object)
    #      a dbxref
    #  ingestSAB: the SAB for a set of assertions.
    #

    # For the majority of nodes, especially those from either UMLS or from OBO-compliant OWL files in RDF/XML serialization,
    # the code format is:
    # <SAB><space><code>

    # However, there are a number of special cases, which are handled below.

    # This script relies on a resource file named prefixes.csv.

    # ---------------
    # DEFAULT
    # Convert the code string to the CodeID format.
    # The colon, underscore, and space characters are reserved as delimters between SAB and code;
    # The hash and backslash figure are delimiters in URIs.
    ret = x.str.replace(':', ' ').str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]

    # --------------
    # SPECIAL CONVERSIONS: UMLS SABS
    # For various reasons, some SABs in the UMLS diverge from the format.
    # A common divergence is the case in which the SAB is included in the code to account for codes with leading zeroes
    #-- e.g., HGNC, GO, HPO
    # NCI
    ret = ret.str.replace('NCIT ', 'NCI ', regex=False)
    # MSH
    ret = ret.str.replace('MESH ', 'MSH ', regex=False)
    # GO
    ret = ret.str.replace('GO ', 'GO GO:', regex=False)
    # NCBI
    ret = ret.str.replace('NCBITaxon ', 'NCBI ', regex=False)
    # UMLS
    ret = ret.str.replace('.*UMLS.*\s', 'UMLS ', regex=True)
    # SNOMED
    ret = ret.str.replace('.*SNOMED.*\s', 'SNOMEDCT_US ', regex=True)
    # HP
    ret = ret.str.replace('HP ', 'HPO HP:', regex=False)
    # FMA
    ret = ret.str.replace('^fma', 'FMA ', regex=True)
    # HGNC
    ret = ret.str.replace('Hugo.owl HGNC ', 'HGNC ', regex=False)
    ret = ret.str.replace('HGNC ', 'HGNC HGNC:', regex=False)
    ret = ret.str.replace('gene symbol report?hgnc id=', 'HGNC HGNC:', regex=False)

    # -------------
    # SPECIAL CASES - Non-UMLS sets of assertions

    ret = np.where(x.str.contains('Thesaurus.owl'), 'NCI ' + x.str.split('#').str[-1], ret)

    # UNIPROTKB
    # The HGNC codes were in the expected format of HGNC HGNC:code. Remove duplications introduced from earlier conversions.
    ret = np.where(x.str.contains('HGNC HGNC:'), x, ret)

    # EDAM has two cases:
    # 1. When obtained from edge file for source or object nodes, EDAM IRIs are in the format
    #    http://edamontology.org/<domain>_<id>
    #    e.g., http://edamontology.org/format_3750
    # 2. When obtained from node file for dbxref, EDAM codes are in the format
    #    EDAM:<domain>_<id>

    # Case 2 (dbxref)
    ret = np.where((x.str.contains('EDAM')), x.str.split(':').str[-1], ret)
    # Case 1 (subject or object node)
    ret = np.where((x.str.contains('edam')), 'EDAM ' + x.str.replace(' ', '_').str.split('/').str[-1], ret)

    # MONDO
    #
    # 1. MONDO identifies genes with IRIs in format
    # http://identifiers.org/hgnc/<id>
    # Convert to HGNC HGNC:<id>
    ret = np.where(x.str.contains('http://identifiers.org/hgnc'),
                   'HGNC HGNC:' + x.str.split('/').str[-1], ret)
    # 2. MONDO uses both OBO-3 compliant IRIs (e.g., "http://purl.obolibrary.org/obo/MONDO_0019052") and
    #    non-compliant ones (e.g., "http://purl.obolibrary.org/obo/mondo#ordo_clinical_subtype")
    ret = np.where(x.str.contains('http://purl.obolibrary.org/obo/mondo#'),
                   'MONDO' + x.str.split('#').str[-1], ret)

    # A number of ontologies, especially those that originate from Turtle files, use prefixes that are
    # translated to IRIs that are not formatted as expected. Obtain the original namespace prefixes for
    # SABs.
    # Read in file of prefix mappings.
    dfPrefix = getPrefixes()
    for index, row in dfPrefix.iterrows():
        if ingestSAB in ['GLYCOCOO','GLYCORDF']:
            ret = np.where(x.str.contains(row['prefix']), row['SAB'] + ' ' +
                           x.str.replace(' ', '_').str.replace('/', '_').str.split('#').str[-1],
                           ret)
        else:
            ret = np.where(x.str.contains(row['prefix']),row['SAB']+' '+x.str.replace(' ', '_').str.replace('/','_').str.replace('=','_').str.split('_').str[-1], ret)

    # UNIPROT (not to be confused with UNIPROTKB).
    ret = np.where(x.str.contains('uniprot.org'), 'UNIPROT ' + x.str.split('/').str[-1], ret)

    # HRAVS
    ret = np.where(x.str.contains('http://purl.humanatlas.io/valueset/'), 'HRAVS ' + x.str.split('/').str[-1], ret)

    # GTEX, which formats the SAB as GTEX_(subcategory) (code).
    ret = np.where(x.str.contains('GTEX_'),x.str.split(' ').str[0]+' '+ x.str.split(' ').str[-1],ret)

    # ---------------
    # FINAL PROCESSING
    # JAS 12 JAN 2023 - Force SAB to uppercase.
    # Some CodeIds will be in format SAB <space> <other string>, and <other string> can be mixed case.
    # <other string> can also have spaces.
    # After all of the preceding conversions, ret is now a numpy array.
    # Split each element; convert the SAB portion to uppercase; and rejoin.
    for idx, x in np.ndenumerate(ret):
        x2 = x.split(sep=' ', maxsplit=1)
        x2[0] = x2[0].upper()
        ret[idx] = ' '.join(x2)
    return ret

    # -------------
    # ORIGINAL CODE for historical purposes

    # return x.str.replace('NCIT ', 'NCI ', regex=False).str.replace('MESH ', 'MSH ', regex=False) \
    # .str.replace('GO ', 'GO GO:', regex=False) \
    # .str.replace('NCBITaxon ', 'NCBI ', regex=False) \
    # .str.replace('.*UMLS.*\s', 'UMLS ', regex=True) \
    # .str.replace('.*SNOMED.*\s', 'SNOMEDCT_US ', regex=True) \
    # .str.replace('HP ', 'HPO HP:', regex=False) \
    # .str.replace('^fma', 'FMA ', regex=True) \
    # .str.replace('Hugo.owl HGNC ', 'HGNC ', regex=False) \
    # .str.replace('HGNC ', 'HGNC HGNC:', regex=False) \
    # .str.replace('gene symbol report?hgnc id=', 'HGNC HGNC:', regex=False)
