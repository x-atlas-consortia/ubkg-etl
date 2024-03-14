"""
Utility to convert a file from CSV to TSV format.
This utility assumes:
1. Files are intended for UBKG Edge/Nodes format, but simply is in CSV format.
2. Files are named OWLNETS_edgelist.txt and OWLNETS_node_metadata.txt
3. Files are in the application directory.

"""

import pandas as pd
import os

print('Converting edge file...')
fpath = 'OWLNETS_edgelist.txt'
df = pd.read_csv(fpath, sep=',',usecols=['subject','predicate','object'])
ftsv = 'edges.tsv'
df.to_csv(ftsv, index=False, sep='\t')

print('Converting node file...')
fpath = 'OWLNETS_node_metadata.txt'
df = pd.read_csv(fpath, sep=',',usecols=['node_id', 'node_label', 'node_namespace', 'node_dbxrefs',
       'upperbound', 'value', 'lowerbound', 'unit', 'node_synonyms',
       'node_definition'])
ftsv = 'nodes.tsv'
df.to_csv(ftsv, index=False, sep='\t')

