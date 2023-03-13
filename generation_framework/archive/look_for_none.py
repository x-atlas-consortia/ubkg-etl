#!/usr/bin/env python

import sys
import pandas as pd
import numpy as np
import base64
import json
import os

base_working_dir = './owlnets_output'
node_metadata_file = 'OWLNETS_node_metadata.txt'


def file_from_uri(uri_str: str) -> str:
    if uri_str.find('/'):
        return uri_str.rsplit('/', 1)[1]


def look_for_none_in_node_metadata_file(file: str) -> None:
    print(f'Searching {file}')
    data = pd.read_csv(file, sep='\t')

    print(f"Total columns: {len(data['node_synonyms'])}")
    node_synonyms_not_None = data[data['node_synonyms'].str.contains('None')==False]
    print(f"Columns where node_synonyms is not None: {len(node_synonyms_not_None)}")
    node_dbxrefs_not_None = data[data['node_dbxrefs'].str.contains('None')==False]
    print(f"Columns where node_dbxrefs is not None: {len(node_dbxrefs_not_None)}")
    both_not_None = node_synonyms_not_None[node_synonyms_not_None['node_dbxrefs'].str.contains('None')==False]
    print(f"Columns where node_synonyms && node_dbxrefs is not None: {len(both_not_None)}")


def look_for_none(uri: str) -> None:
    working_file = file_from_uri(uri)
    working_dir = base_working_dir + os.path.sep + working_file.rsplit('.', 1)[0]
    look_for_none_in_node_metadata_file(working_dir + os.path.sep + node_metadata_file)


none_total = 0
field = 'node_label'
files = sys.argv[1:]
for file in files:
    data = pd.read_csv(file, sep='\t')
    field_None = data[data[field].str.contains('None')==True]
    print(f"Columns where \'{field}\' in {file} is None: {len(field_None)}")
    none_total += len(field_None)
print(f"Total of {none_total} None entries for field \'{field}\' in files: {files}")

#look_for_none_in_file(sys.argv[1])
print('Done!')
