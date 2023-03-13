#!/usr/bin/env python

import os
import glob
import logging.config
import time
from datetime import timedelta
from transforms import Transforms

import pandas as pd

log_dir, log, log_config = 'builds/logs', 'pkt_build_log.log', glob.glob('**/logging.ini', recursive=True)
logger = logging.getLogger(__name__)
logging.config.fileConfig(log_config[0], disable_existing_loggers=False, defaults={'log_file': log_dir + '/' + log})

# https://uberon.github.io/downloads.html
# Use the simpler one first....
uberon_owl_url = 'http://purl.obolibrary.org/obo/uberon.owl'
# Use this data (the extended version)...
# uberon_ext_owl_url = 'http://purl.obolibrary.org/obo/uberon/ext.owl'

uri = uberon_owl_url

base_working_dir = './owlnets_output'


def find_file_with_ext(dir: str, dotted_ext: str) -> list:
    files = []
    for file in os.listdir(dir):
        if file.endswith(dotted_ext):
            path = os.path.join(dir, file)
            files.append(path)
    return files


transforms = Transforms()

working_file = transforms.file_from_uri(uri)
working_dir = base_working_dir + os.path.sep + working_file.rsplit('.', 1)[0]

# Dictionary data structure...
# relation entities, edges, and definitions

# gpickle graph don't want it
# .nt file is probably the same content as
# Concentrate: edgeslist.txt, node_metadata.txt, relations.txt, and .pkl file
# in RDF (OWL files) everything is a tripple (edgelist and edge file
pkl_file = find_file_with_ext(working_dir, '.pkl')
start_time = time.time()
logger.info("Processing '%s'", pkl_file[0])

# https://docs.python.org/3/library/pickle.html
df = pd.read_pickle(pkl_file[0])

print(list(df.keys()))

# Everything important is here?! Synonyms, names, codes, edges.
list(df['devoded_entries'].keys())[0]

elapsed_time = time.time() - start_time
logger.info('Done! Elapsed time %s', "{:0>8}".format(str(timedelta(seconds=elapsed_time))))
