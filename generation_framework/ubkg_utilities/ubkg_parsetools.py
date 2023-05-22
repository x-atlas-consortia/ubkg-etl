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

    # Find absolute path to file.
    file = 'prefixes.csv'
    fpath = os.path.dirname(os.getcwd())
    fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities',file)
    df = pd.DataFrame()

    if os.path.exists(fpath):
        # This is being called by build_csv.py.
        df= pd.read_csv(fpath)
    elif os.path.exists(file):
        # This is being called by the local parsetester.py script.
        df = pd.read_csv(file)
    else:
        # Using print here instead of logging to allow functioning with parsetester.py.
        print('ubkg_parsetools: missing prefixes.csv file in the ubkg_utilities directory.')

    return df

def codeReplacements(x:pd.Series, ingestSAB: str):

    # JAS 15 Nov 2022 - Refactor

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
    # NCI Thesaurus
    ret = ret.str.replace('NCIT ', 'NCI ', regex=False)
    # MESH
    ret = ret.str.replace('MESH ', 'MSH ', regex=False)
    # GO
    ret = ret.str.replace('GO ', 'GO GO:', regex=False)
    # NCBI Taxonomy
    ret = ret.str.replace('NCBITaxon ', 'NCBI ', regex=False)
    # UMLS
    ret = ret.str.replace('.*UMLS.*\s', 'UMLS ', regex=True)
    # SNOMED
    ret = ret.str.replace('.*SNOMED.*\s', 'SNOMEDCT_US ', regex=True)
    # HPO
    ret = ret.str.replace('HP ', 'HPO HP:', regex=False)
    # FMA
    ret = ret.str.replace('^fma', 'FMA ', regex=True)
    # HGNC
    # Note that non-UMLS sets of assertions may also refer to HGNC codes differently. See below.
    ret = ret.str.replace('Hugo.owl HGNC ', 'HGNC ', regex=False)
    ret = ret.str.replace('HGNC ', 'HGNC HGNC:', regex=False)
    ret = ret.str.replace('gene symbol report?hgnc id=', 'HGNC HGNC:', regex=False)


    # -------------
    # SPECIAL CASES - Non-UMLS sets of assertions

    # Ontologies such as HRAVS refer to NCI Thesaurus nodes by IRI.
    ret = np.where(x.str.contains('Thesaurus.owl'), 'NCI ' + x.str.split('#').str[-1], ret)

    # UNIPROTKB
    # The HGNC codes in the UNIPROTKB ingest files were in the expected format of HGNC HGNC:code.
    # Remove duplications introduced from earlier conversions in this script.
    ret = np.where(x.str.contains('HGNC HGNC:'), x, ret)

    # EDAM
    # EDAM uses subdomains--e.g, format_3750, which translates to a SAB of "format". Force all
    # EDAM nodes to be in a SAB named EDAM.

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
    # Two cases to handle:
    # 1. MONDO identifies genes with IRIs in format
    # http://identifiers.org/hgnc/<id>
    # Convert to HGNC HGNC:<id>
    ret = np.where(x.str.contains('http://identifiers.org/hgnc'),
                   'HGNC HGNC:' + x.str.split('/').str[-1], ret)
    # 2. MONDO uses both OBO-3 compliant IRIs (e.g., "http://purl.obolibrary.org/obo/MONDO_0019052") and
    #    non-compliant ones (e.g., "http://purl.obolibrary.org/obo/mondo#ordo_clinical_subtype")
    ret = np.where(x.str.contains('http://purl.obolibrary.org/obo/mondo#'),
                   'MONDO ' + x.str.split('#').str[-1], ret)

    # MAY 2023
    # PGO
    # Restore changes made related to GO
    ret = np.where(x.str.contains('PGO'),
                   'PGO ' + x.str.split('/').str[-1], ret)

    # REFSEQ - keep underscores
    ret = np.where(x.str.contains('REFSEQ:'),
                   'REFSEQ ' + x.str.split(':').str[-1], ret)

    # PREFIXES
    # A number of ontologies, especially those that originate from Turtle files, use prefixes that are
    # translated to IRIs that are not formatted as expected. Obtain the original namespace prefixes for
    # SABs.
    # Read in file of prefix mappings.
    dfPrefix = getPrefixes()
    # Convert for each of the prefixes.
    for index, row in dfPrefix.iterrows():
        if ingestSAB in ['GLYCOCOO','GLYCORDF']:
            #GlyCoCOO (a Turtle) and GlyCoRDF use IRIs that delimit with hash and use underlines.
            #"http://purl.glycoinfo.org/ontology/codao#Compound_disease_association
            ret = np.where(x.str.contains(row['prefix']), row['SAB'] + ' ' +
                           x.str.replace(' ', '_').str.replace('/', '_').str.split('#').str[-1],
                           ret)
        else:
            # Other SABs format IRIs with a terminal backslash and the code string.
            # A notable exception is the PantherDB format (in NPOSKCAN), for which the IRI is an API call
            # (e.g., http://www.pantherdb.org/panther/family.do?clsAccession=PTHR10558).
            ret = np.where(x.str.contains(row['prefix']), row['SAB'] + ' ' +
                           x.str.replace(' ', '_').str.replace('/','_').str.replace('=','_').str.split('_').str[-1],
                           ret)

    # UNIPROT (not to be confused with UNIPROTKB).
    # UNIPROT IRIs are formatted differently than those in Glygen, but are in the Glygen OWL files, so they need
    # to be translated separately from GlyGen nodes.
    ret = np.where(x.str.contains('uniprot.org'), 'UNIPROT ' + x.str.split('/').str[-1], ret)

    #JAS MAY 2023 - For case of HGNC codes added as dbxrefs.
    ret = np.where(x.str.contains('HGNC HGNC '), x.str.replace('HGNC HGNC ','HGNC HGNC:'), ret)

    # ---------------
    # FINAL PROCESSING
    # JAS 12 JAN 2023 - Force SAB to uppercase.
    # Some CodeIds will be in format SAB <space> <other string>, and <other string> can be mixed case.
    # <other string> can also have spaces.
    # After the preceding conversions, ret has changed from a Pandas Series to a numpy array.
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
