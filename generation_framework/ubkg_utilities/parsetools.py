#!/usr/bin/env python
# coding: utf-8
import numpy as np


# UBKG utilities for parsing

# codeReplacements - shared by at least the following scripts:
# OWLNETS-UMLS-GRAPH
# skowlnets

def codeReplacements(x, ingestSAB: str):
    # JAS 15 Nov 2022 - Refactor

    # This function converts strings that correspond to either codes or CUIs for concepts to a format
    # recognized by the knowledge graph.
    #
    # For most concepts this format is:
    # <SAB><space><code>
    # There are a number of special cases, which are handled below.

    # The argument x is a Pandas Series object containing information on either:
    #  a node (subject or object)
    #  a dbxref

    # 1. Account for special cases of
    #   a. MONDO
    #   b. EDAM
    #   c. JAS 13 JAN 2023 - UNIPROT
    # 2. Consolidate some string handling.
    # 3. Break up the original string replacement for ease of debugging.

    # Convert the code string to the CodeID format.
    # This is sufficient for all cases except EDAM, for which underscores will be restored.
    ret = x.str.replace(':', ' ').str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]

    # Convert SABs to expected values.
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

    # Special case:
    # MONDO identifies genes with IRIs in format
    # http://identifiers.org/hgnc/<id>
    # Convert to HGNC HGNC:<id>
    ret = np.where((ingestSAB == 'MONDO' and x.str.contains('http://identifiers.org/hgnc')),
                   'HGNC HGNC:' + x.str.split('/').str[-1], ret)

    # Special cases: EDAM codes.
    # 1. When obtained from edge file for source or object nodes, EDAM IRIs are in the format
    #    http://edamontology.org/<domain>_<id>
    #    e.g., http://edamontology.org/format_3750
    # 2. When obtained from node file for dbxref, EDAM codes are in the format
    #    EDAM:<domain>_<id>

    # Force the SAB to be EDAM and restore the underscore delimiter between domain and id.
    # ret = np.where((x.str.contains('http://edamontology.org')),
    # 'EDAM ' + x.str.replace(':', ' ').str.replace('#', ' ').str.split('/').str[-1]
    # , ret)

    # Case 2
    ret = np.where((x.str.contains('EDAM')), x.str.split(':').str[-1], ret)
    # Case 1
    ret = np.where((x.str.contains('edam')), 'EDAM ' + x.str.replace(' ', '_').str.split('/').str[-1], ret)

    # JAS JAN 2023 - Special case: Glyco Glycan
    # Glycan node IRIs are in format:
    # http://purl.jp/bio/12/glyco/glycan#(code delimited with underscore)
    # Force the SAB to be GLYCO.GLYCAN and restore the underscore delimiter between domain and id.
    ret = np.where((x.str.contains('http://purl.jp/bio/12/glyco/glycan')),
                   'GLYCO.GLYCAN ' + x.str.replace(' ', '_').str.replace('#', '/').str.split('/').str[-1], ret)

    # JAS JAN 2023 - Special case: Glyco Conjugate
    # Glycan node IRIs are in format:
    # http://purl.jp/bio/12/glyco/conjugate#(code delimited with underscore)
    # Force the SAB to be GLYCO.CONJUGATE and restore the underscore delimiter between domain and id.
    ret = np.where((x.str.contains('http://purl.jp/bio/12/glyco/conjugate')),
                   'GLYCO.CONJUGATE ' + x.str.replace(' ', '_').str.replace('#', '/').str.split('/').str[-1], ret)

    # JAS JAN 2023 - Special case: NCBI's GENE database
    # Node IRIs for genes in NCBI GENE are in format
    # http: // www.ncbi.nlm.nih.gov / gene / 19091
    # FEB 2023
    # NCBI Gene IDs are currently stored in the NCI SAB obtained from UMLS, with code IDs that
    # prepend a 'C' to the Gene ID.
    # Until we ingest NCBI Gene directly, map to NCI format.
    ret = np.where(x.str.contains('http://www.ncbi.nlm.nih.gov/gene'), 'NCI' + 'C' + x.str.split('/').str[-1], ret)

    # JAS JAN 2023 - Special case: NIFSTD
    # As with EDAM, Node IRIs for codes from NIFSTD show domains--e.g.,
    # http://uri.neuinfo.org/nif/nifstd/nlx_149264, where "nlx" is the domain
    # Unify codes under the SAB NIFSTD and restore the underscore delimiter between domain and id.
    ret = np.where(x.str.contains('http://uri.neuinfo.org/nif/nifstd'),
                   'NIFSTD' + x.str.replace(' ', '_').str.split('/').str[-1], ret)

    # Special case:
    # HGNC codes in expected format--i.e., that did not need to be converted above.
    # This is currently the case for UNIPROTKB.
    ret = np.where(x.str.contains('HGNC HGNC:'), x, ret)

    # JAS 13 JAN 2023 - Special case: UNIPROT (not to be confused with UNIPROTKB).
    # The Uniprot OWL node IRIs do not conform to OBO, so set SAB explicitly.
    ret = np.where(x.str.contains('http://purl.uniprot.org'), 'UNIPROT ' + x.str.split('/').str[-1], ret)

    # JAS JAN 2023 - Special case: HRAVS
    ret = np.where(x.str.contains('http://purl.humanatlas.io/valueset/'), 'HRAVS ' + x.str.split('/').str[-1], ret)
    ret = np.where(x.str.contains('Thesaurus.owl'), 'NCI ' + x.str.split('#').str[-1], ret)

    # JAS 12 JAN 2023 - Force SAB to uppercase.
    # The CodeId will be in format SAB <space> <other string>, and <other string> can be mixed case.
    # <other string> can also have spaces.
    # ret is now a numpy array.
    # Split each element; convert the SAB portion to uppercase; and rejoin.
    for idx, x in np.ndenumerate(ret):
        x2 = x.split(sep=' ', maxsplit=1)
        x2[0] = x2[0].upper()
        ret[idx] = ' '.join(x2)
    return ret

    # original code
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
