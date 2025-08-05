#!/usr/bin/env python
# coding: utf-8
import numpy as np
import pandas as pd
import os

# UBKG logging utility
import ubkg_logging as ulog

# UBKG utilities for parsing

# codeReplacements - shared by at least the following scripts:
# OWLNETS-UMLS-GRAPH
# skowlnets


def getprefixes() -> pd.DataFrame:
    # Reads a resource file of SAB/prefixes.

    # Find absolute path to file.
    file = 'prefixes.csv'
    fpath = os.path.dirname(os.getcwd())
    fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities', file)
    df = pd.DataFrame()

    if os.path.exists(fpath):
        # This is being called by build_csv.py.
        df = pd.read_csv(fpath)
    elif os.path.exists(file):
        # This is being called by the local parsetester.py script.
        df = pd.read_csv(file)
    else:
        # Using print here instead of logging to allow functioning with parsetester.py.
        print('ubkg_parsetools: missing prefixes.csv file in the ubkg_utilities directory.')

    return df


def codeReplacements(x: pd.Series, ingestSAB: str):

    # This function converts strings that correspond to either codes or CUIs for concepts to a format
    # recognized by the knowledge graph.

    # The standard format is SAB:code.

    # Arguments:
    #  x - Pandas Series object containing information on either:
    #      a node (subject or object)
    #      a dbxref
    #  ingestSAB: the SAB for a set of assertions.
    #

    # JULY 2023 -
    # 1. Assume that data from SABs from UMLS have been reformatted so that
    #    HGNC HGNC:CODE -> HGNC CODE
    #    GO GO:CODE -> GO CODE
    #    HPO HP:CODE -> HPO CODE
    # 2. Establishes the colon as the exclusive delimiter between SAB and code.
    # -------

    # Because of the variety of formats used for codes in various sources, this standardization is
    # complicated.

    # For the majority of nodes, especially those from either UMLS or from OBO-compliant OWL files in RDF/XML
    # serialization,
    # the formatting is straightforward. However, there are a number of special cases, which are handled below.

    # For some SABs, the reformatting is complicated enough to warrant a resource file named prefixes.csv, which
    # should be in the application folder.

    # ---------------
    # DEFAULT
    # Convert the code string to the CodeID format.
    # The colon, underscore, and space characters are reserved as delimters between SAB and code in input sources--e.g.,
    #   SAB:CODE
    #   SAB_CODE
    #   SAB CODE
    # However, the underscore is also used in code strings in some cases--e.g., RefSeq, with REFSEQ:NR_number.

    # In addition, the hash and backslash figure are delimiters in URIs--e.g., ...#/SAB_CODE

    # Start by reformatting as SAB<space>CODE. The exclusive delimiter (colon) will be added at the end of this
    # script.
    ret = x.str.replace(':', ' ').str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]

    # --------------
    # SPECIAL CONVERSIONS: UMLS SABS
    # 1. Standardize SABs--e.g., convert NCBITaxon (from IRIs) to NCBI (in UMLS); MESH to MSH; etc.
    # 2. For various reasons, some SABs in the UMLS diverge from the standard format.
    #    A common divergence is the case in which the SAB is included in the code to account
    #    for codes with leading zeroes
    #    -- e.g., HGNC, GO, HPO

    # July 2023 - replaced space with colon for delimiter.

    # NCI Thesaurus
    ret = ret.str.replace('NCIT ', 'NCI:', regex=False)
    # MESH
    ret = ret.str.replace('MESH ', 'MSH:', regex=False)

    # GO (conversion deprecated July 2023; incoming format is now GO:code)
    # ret = ret.str.replace('GO ', 'GO GO:', regex=False)

    # NCBI Taxonomy
    ret = ret.str.replace('NCBITaxon ', 'NCBI:', regex=False)
    # UMLS
    ret = ret.str.replace('.*UMLS.*\s', 'UMLS:', regex=True)
    # SNOMED
    ret = ret.str.replace('.*SNOMED.*\s', 'SNOMEDCT_US:', regex=True)

    # HPO (deprecated July 2023; incoming format is now HPO:CODE)
    # ret = ret.str.replace('HP ', 'HPO HP:', regex=False)

    # FMA
    ret = ret.str.replace('^fma', 'FMA:', regex=True)

    # HGNC
    # Note that non-UMLS sets of assertions may also refer to HGNC codes differently. See below.
    ret = ret.str.replace('Hugo.owl HGNC ', 'HGNC:', regex=False)

    # Deprecated July 2023; the incoming format is now HGNC:code.
    # ret = ret.str.replace('HGNC ', 'HGNC HGNC:', regex=False)
    # Changed July 2023
    # ret = ret.str.replace('gene symbol report?hgnc id=', 'HGNC HGNC:', regex=False)
    ret = ret.str.replace('gene symbol report?hgnc id=', 'HGNC:', regex=False)

    # -------------
    # SPECIAL CASES - Non-UMLS sets of assertions

    # Ontologies such as HRAVS refer to NCI Thesaurus nodes by IRI.
    ret = np.where(x.str.contains('Thesaurus.owl'), 'NCI:' + x.str.split('#').str[-1], ret)

    # UNIPROTKB
    # The HGNC codes in the UNIPROTKB ingest files were in the expected format of HGNC HGNC:code.
    # Remove duplications introduced from earlier conversions in this script.
    # Deprecated July 2023: incoming format is now HGNC:code.
    # ret = np.where(x.str.contains('HGNC HGNC:'), x, ret)

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
    ret = np.where((x.str.contains('edam')), 'EDAM:' + x.str.replace(' ', '_').str.split('/').str[-1], ret)

    # MONDO
    # Two cases to handle:
    # 1. MONDO identifies genes with IRIs in format
    # http://identifiers.org/hgnc/<id>
    # Convert to HGNC HGNC:<id>
    # Changed July 2023
    # ret = np.where(x.str.contains('http://identifiers.org/hgnc'),
                   #'HGNC HGNC:' + x.str.split('/').str[-1], ret)
    ret = np.where(x.str.contains('http://identifiers.org/hgnc'),
                   'HGNC:' + x.str.split('/').str[-1], ret)
    # 2. MONDO uses both OBO-3 compliant IRIs (e.g., "http://purl.obolibrary.org/obo/MONDO_0019052") and
    #    non-compliant ones (e.g., "http://purl.obolibrary.org/obo/mondo#ordo_clinical_subtype")
    ret = np.where(x.str.contains('http://purl.obolibrary.org/obo/mondo#'),
                   'MONDO:' + x.str.split('#').str[-1], ret)

    # MAY 2023
    # PGO
    # Restore changes made related to GO.
    # PGO nodes are written as http://purl.obolibrary.org/obo/PGO_(code)
    # Deprecated July 2023
    # ret = np.where(x.str.contains('PGO'),
                   # 'PGO PGO:' + x.str.split('_').str[-1], ret)

    # REFSEQ - restore underscore between NR and number.
    # JULY 2023 - Refactored for SAB:CODE refactoring
    # Assumes that code at this point is in format REFSEQ NR X, to be reformatted as REFSEQ:NR_X.
    ret = np.where(x.str.contains('REFSEQ'), x.str.replace('REFSEQ ', 'REFSEQ:').str.replace(' ', '_'), ret)

    # July 2023
    # MSIGDB - restore underscores.
    ret = np.where(x.str.contains('MSIGDB'), x.str.replace('MSIGDB ', 'MSIGDB:').str.replace(' ', '_'), ret)

    # January 2025
    # REACTOME - restore underscores.
    ret = np.where(x.str.contains('REACTOME'), x.str.replace('REACTOME ', 'REACTOME:').str.replace(' ', '_'), ret)


    # MAY 2023
    # HPO
    # If expected format (HPO HP:code) was used, revert to avoid duplication.
    # Deprecated July 2023: incoming code format now HPO:CODE.
    # ret = np.where(x.str.contains('HPO HP:'),
                    #'HPO HP:' + x.str.split(':').str[-1], ret)

    # HCOP
    # The HCOP node_ids are formatted to resemble HGNC node_ids.
    # Deprecated July 2023; no longer needed because HGNC is now formatted as HGNC:CODE.
    # ret = np.where(x.str.contains('HCOP'),'HCOP HCOP:' + x.str.split(':').str[-1],ret)

    # SEPT 2023
    # CEDAR
    ret = np.where(x.str.contains('https://repo.metadatacenter.org/templates/'),
                   'CEDAR:' + x.str.split('/').str[-1], ret)
    ret = np.where(x.str.contains('https://repo.metadatacenter.org/template-fields/'),
                   'CEDAR:' + x.str.split('/').str[-1], ret)
    ret = np.where(x.str.contains('https://schema.metadatacenter.org/core/'),
                   'CEDAR:' + x.str.split('/').str[-1], ret)
    ret = np.where(x.str.contains('http://www.w3.org/2001/XMLSchema'),
                   'XSD:' + x.str.split('#').str[-1], ret)

    # HRAVS
    # The HRAVS IRIs are in format ...hravs#HRAVS_X, which results in HRAVS HRAVS X.
    ret = np.where(x.str.contains('https://purl.humanatlas.io/vocab/hravs#'),
                   'HRAVS:' + x.str.split('_').str[-1], ret)
    # The gzip_csv converter script translates HRAVS IRIs to hravs HRAVS X.
    ret = np.where(x.str.upper().str.contains('HRAVS HRAVS'),
                   'HRAVS:' + x.str.split(' ').str[-1], ret)

    # ORDO
    # ORDO uses Orphanet as a namespace.
    ret = np.where(x.str.contains('http://www.orpha.net/ORDO/'),
                   'ORDO:' + x.str.split('_').str[-1], ret)


    # PREFIXES
    # A number of ontologies, especially those that originate from Turtle files, use prefixes that are
    # translated to IRIs that are not formatted as expected. Obtain the original namespace prefixes for
    # SABs.
    # Read in file of prefix mappings.
    dfPrefix = getprefixes()
    # Convert for each of the prefixes.
    for index, row in dfPrefix.iterrows():
        if ingestSAB in ['GLYCOCOO', 'GLYCORDF']:
            # GlyCoCOO (a Turtle) and GlyCoRDF use IRIs that delimit with hash and use underlines.
            # "http://purl.glycoinfo.org/ontology/codao#Compound_disease_association
            # July 2023 - refactored to use colon as SAB:code delimiter
            ret = np.where(x.str.contains(row['prefix']), row['SAB'] + ':' +
                           x.str.replace(' ', '_').str.replace('/', '_').str.split('#').str[-1],
                           ret)
        # July 2023: other prefixes are only from NPO, NPOSKCAN
        else:
            if ingestSAB in ['NPO', 'NPOSKCAN']:
                # Other SABs format IRIs with a terminal backslash and the code string.
                # A notable exception is the PantherDB format (in NPOSKCAN), for which the IRI is an API call
                # (e.g., http://www.pantherdb.org/panther/family.do?clsAccession=PTHR10558).
                # July 2023 - refactored to use colon as SAB:code delimiter
                ret = np.where(x.str.contains(row['prefix']), row['SAB'] + ':' +
                               x.str.replace(' ', '_').str.replace('/', '_').str.replace('=', '_').str.split('_').str[-1],
                               ret)

    # UNIPROT (not to be confused with UNIPROTKB).
    # UNIPROT IRIs are formatted differently than those in Glygen, but are in the Glygen OWL files, so they need
    # to be translated separately from GlyGen nodes.
    # July 2023 - refactored to use colon as SAB:code delimiter
    ret = np.where(x.str.contains('uniprot.org'), 'UNIPROT:' + x.str.split('/').str[-1], ret)

    # JAS MAY 2023 - For case of HGNC codes added as dbxrefs.
    # Deprecated July 2023; incoming codes have format HGNC:CODE.
    # ret = np.where(x.str.contains('HGNC HGNC '), x.str.replace('HGNC HGNC ','HGNC HGNC:'), ret)

    # June 2023 - CCF, which uses underscores in codes
    # (Deprecated after we switched from CCF to HRA)
    # ret = np.where(x.str.contains('http://purl.org/ccf/'),'CCF ' + x.str.split('/').str[-1], ret)
    # HGNCNR was a dependency for CCF, so also deprecated
    # ret = np.where(x.str.contains('http://purl.bioontology.org/ontology/HGNC/'), 'HGNCNR ' + x.str.split('/').str[-1], ret)

    # July 2023 - For Data Distillery use cases, where code formats conformed to the earlier paradigms.
    # HGNC HGNC:
    # HPO HP:
    # HCOP HCOP:
    ret = np.where(x.str.contains('HGNC HGNC:'), x.str.replace('HGNC HGNC:', 'HGNC:'), ret)
    # January 2024 - standardized to HP from HPO.
    ret = np.where(x.str.contains('HPO HP:'), x.str.replace('HPO HP:', 'HP:'), ret)
    ret = np.where(x.str.contains('HCOP HCOP:'), x.str.replace('HCOP HCOP:', 'HCOP:'), ret)

    ret = np.where(x.str.contains('NCBI Gene'), x.str.replace('NCBI Gene', 'ENTREZ:'), ret)

    # JANUARY 2024 - GENCODE_VS
    # Restore the underscore.
    ret = np.where(x.str.contains('GENCODE_VS'),x.str.replace('GENCODE:VS', 'GENCODE_VS'), ret)

    # AUGUST 2025 - SENOTYPE_VS
    # Restore the underscore.
    ret = np.where(x.str.contains('SENOTYPE_VS'), x.str.replace('SENOTYPE:VS', 'SENOTYPE_VS'), ret)

    # ---------------
    # FINAL PROCESSING

    # At this point in the script, the code should be in one of two formats:
    # 1. SAB CODE, where
    #    a. SAB may be lowercase
    #    b. CODE may be mixed case, wiht spaces.
    # 2. The result of a custom formatting--e.g., HGNC:code.

    # The assumption is that if there are spaces at this point, the first space is the one between the SAB
    # and the code.

    # Force SAB to uppercase. Force the colon to be the delimiter between SAB and code.

    # After the preceding conversions, ret has changed from a Pandas Series to a numpy array.
    # 1. Split each element on the initial space, if one exists.
    # 2. Convert the SAB portion (first element) to uppercase.
    # JULY 2023
    # 3. Add the colon between the SAB (first element) and the code.

    # Note: Special cases should already be in the correct code format of SAB:code.

    for idx, x in np.ndenumerate(ret):
        xsplit = x.split(sep=' ', maxsplit=1)
        if len(xsplit) > 1:
            sab = xsplit[0].upper()
            code = ' '.join(xsplit[1:len(xsplit)])
            ret[idx] = sab+':'+code
        elif len(x)>0:
            # JULY 2023
            # For the case of a CodeID that appears to be a "naked" UMLS CUI, format as UMLS:CUI.
            # SEPT 2023 - Account for codes in the CEDAR SAB.
            if x[0] == 'C' and not 'CEDAR' in x and x[1].isnumeric:
             ret[idx] = 'UMLS:'+x
        else:
            ret[idx] = x

    return ret

    # -------------
    # ORIGINAL CODE for historical purposes. Life was simpler then.

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

def relationReplacements(x: pd.Series):

    # This function converts strings that correspond to a predicate string to a format recognized by the generation
    # framework

    # Arguments:
    #  x - Pandas Series object containing predicates (edges)

    # SEPT 2023 - Added replacements for rdf#type IRIs.

    # AUGUST 2023
    # Replace . and - with _

    # JANUARY/Feburary 2024
    # Format relationship strings to comply with neo4j naming rules:
    # 1. Only alphanumeric characters or the underscore.
    # 2. Prepend "rel_" to relationships with labels that start with numbers.
    #



    ret = x.str.replace('.', '_', regex=False)
    ret = ret.str.replace('-', '_', regex=False)
    ret = ret.str.replace('(', '_', regex=False)
    ret = ret.str.replace(')', '_', regex=False)
    ret = ret.str.replace('[', '_', regex=False)
    ret = ret.str.replace(']', '_', regex=False)
    ret = ret.str.replace('{', '_', regex=False)
    ret = ret.str.replace('}', '_', regex=False)
    ret = ret.str.replace(':', '_', regex=False)

    ret = ret.str.lower()
    ret = np.where(ret.astype(str).str[0].str.isnumeric(),'rel_' + ret, ret)


    # For the majority of edges, especially those from either UMLS or from OBO-compliant
    # OWL files in RDF/XML serialization,
    # the format of an edge is one of the following:
    # 1. A IRI in the form http://purl.obolibrary.org/obo/RO_code
    # 2. RO_code
    # 3. RO:code
    # 4. a string

    # March 2024 predicates are in lowercase.
    # ret = np.where(x.str.contains('RO:'), 'http://purl.obolibrary.org/obo/RO_' + x.str.split('RO:').str[-1], ret)
    ret = np.where(x.str.contains('ro:'), 'http://purl.obolibrary.org/obo/ro_' + x.str.split('ro:').str[-1], ret)

    # Replace #type from RDF schemas with isa.
    ret = np.where(x.str.contains('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), 'isa', ret)
    ret = np.where(x.str.contains('http://www.w3.org/2000/01/rdf-schema#type'), 'isa', ret)

    return ret

def parse_string_nested_parentheses(strparen: str) -> list[tuple]:

    """
    Analyzes a string with nested parentheses in terms of level of nesting.

    For example, '(a(b(c)(d)e)(f)g)' can be analyzed as:
    level 0: a(b(c)(d)e)(f)g
    level 1: f
    level 1: b(c)(d)e
    level 2: c
    level 2: d
    or
    [(2, 'c'), (2, 'd'), (1, 'b(c)(d)e'), (1, 'f'), (0, 'a(b(c)(d)e)(f)g')]

    UBKG use case: UniprotKB, which uses parentheses both as delimiters and
    inside elements--e.g., (element 1 (details))(element 2 (details))

    Adapted from a solution posted by Gareth Rees at
    https://stackoverflow.com/questions/4284991/parsing-nested-parentheses-in-python-grab-content-by-level

    """
    return list(parenthetic_contents(strparen))

def parenthetic_contents(strparen: str) -> tuple:

    # Employs a stack to analyze elements in a string by level of nesting.
    stack = []
    for i, c in enumerate(strparen):
        if c == '(':
            # New level of parenthesis nesting.
            stack.append(i)
        elif c == ')' and stack:
            # Closing of element at this level of nesting.
            # Return to higher level of nesting.
            start = stack.pop()
            yield (len(stack), strparen[start + 1: i])
