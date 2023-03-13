#!/usr/bin/env python

from typing import List

import argparse
import os
import glob
import logging.config
import time
from datetime import timedelta
import hashlib
from base64 import urlsafe_b64encode


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


# https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(
    description='Build the files in a manner similar to the way that the PheKnowLator would build them from the\n'
                'Uniprot Filtered Organizm file',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument('input_tsv', type=str,
                    help='the input tsv file to use to create the owlnets files')
parser.add_argument("-s", "--sab", type=str, default='UNIPROTKB',
                    help='the sab to use for this Ontology')
parser.add_argument("-d", "--owlnets_dir", type=str, default='./owlnets_output',
                    help='directory used for the owlnets output files')
parser.add_argument("-r", "--rec_sep", type=str, default='\t',
                    help='record separator')
parser.add_argument("-c", "--clean", action="store_true",
                    help='clean the OELNETS_DIR/SAB directory before run')
parser.add_argument("-v", "--verbose", action="store_true",
                    help='increase output verbosity')
args = parser.parse_args()

rec_sep: str = args.rec_sep

log_dir, log, log_config = 'builds/logs', 'pkt_build_log.log', glob.glob('**/logging.ini', recursive=True)
logger = logging.getLogger(__name__)
logging.config.fileConfig(log_config[0], disable_existing_loggers=False, defaults={'log_file': log_dir + '/' + log})

start_time = time.time()

owlnets_path: str = os.path.join(args.owlnets_dir, args.sab)
if args.clean is True:
    os.system(f"rm -rf {owlnets_path}")
os.system(f"mkdir -p {owlnets_path}")

# subject(UNIPROTKB_inpur_tsv:Entry)	predicate(UNIPROTKB_code)	object(UNIPROTKB_code)
# NOTE: If the protein has no gene name throw it away because it will be isolated.
edgelist_path: str = os.path.join(owlnets_path, 'OWLNETS_edgelist.txt')

# node_id(UNIPROTKB_inpur_tsv:Entry)	node_namespace(UNIPROTKB)	node_label(inpur_tsv:Entry)	node_definition(text)	node_synonyms(text|text)	node_dbxrefs(cui|cui)
node_metadata_path: str = os.path.join(owlnets_path, 'OWLNETS_node_metadata.txt')

# relation_id(sab_code)     relation_namespace(sab)      relation_label(verb)  relation_definition(text)
relations_path: str = os.path.join(owlnets_path, 'OWLNETS_relations.txt')

# https://pitt-my.sharepoint.com/:u:/r/personal/jos220_pitt_edu/Documents/HuBMAP-Knowledge-Graph/uniprot-database%253A%2528type%253AHGNC%2529.tab?csf=1&web=1&e=ZqifvM
# Entry(code)   Status(ignore)  Organism(ignoe) Gene_names_primary(node_dbxrefs)    Protein_names(string)
# NOTE: Status is usually 'unreviewed'; Organism is usually 'Homo sapiens (Human)'
input_tsv_path: str = os.path.join('.', args.input_tsv)

entry_to_gene_relation_id: str = 'has_gene'
entry_to_gene_relation_label: str = 'has gene'
gene_to_protein_relation_id: str = 'expressed_as'
gene_to_protein_relation_label: str = 'expressed as'

proteins_node_ids: dict = {}


def base64it(x: str) -> str:
   return urlsafe_b64encode(str(x).encode('UTF-8')).decode('ascii')


# Because the 'proteins' is really a description, a unique label is needed for it...
def protein_metadata_node_id(fp, proteins: str) -> str:
    global proteins_node_ids
    if proteins in proteins_node_ids:
        return proteins_node_ids[proteins]
    proteins_node_id: str = hashlib.md5(proteins.encode()).hexdigest()
    proteins_node_ids[proteins] = proteins_node_id
    write_node_metadata(fp, proteins_node_id, 'Protein', proteins)
    return proteins_node_id


def write_node_metadata(fp, node_id: str, node_label: str, node_definition: str) -> None:
    # node_id node_namespace  node_label      node_definition node_synonyms   node_dbxrefs
    fp.write(f'{args.sab}_{node_id}{rec_sep}'
             f'{args.sab}{rec_sep}'
             f'{node_label}{rec_sep}'
             f'{node_definition}{rec_sep}'
             f'None{rec_sep}'
             f'None{rec_sep}\n')
    
    
def write_edge(fp, subject: str, predicate: str, object: str) -> None:
    # Subject, Predicate, Object
    fp.write(f'{args.sab}_{subject}{rec_sep}'
             f'{args.sab}_{predicate}{rec_sep}'
             f'{args.sab}_{object}\n')


def write_edges(fp, entry: str, gene: str, proteins: str) -> None:
    write_edge(fp, entry, entry_to_gene_relation_id, gene)
    write_edge(fp, gene, gene_to_protein_relation_id, proteins)


def write_relations_file(fp) -> None:
    # relation_id     relation_namespace      relation_label  relation_definition
    fp.write(f'{entry_to_gene_relation_id}{rec_sep}'
             f'{args.sab}{rec_sep}'
             f'{entry_to_gene_relation_label}{rec_sep}'
             f'None\n')
    fp.write(f'{gene_to_protein_relation_id}{rec_sep}'
             f'{args.sab}{rec_sep}'
             f'{gene_to_protein_relation_label}{rec_sep}'
             f'None\n')


# Entry   Status  Organism        Gene names  (primary )  Protein names
def parse_line(line: str):
    records = line.split(rec_sep)
    entry: str = records[0]
    gene: str = records[3]
    proteins: str = records[4]
    return entry, gene, proteins


input_tsv_fp = open(input_tsv_path, 'r')

edgelist_fp = open(edgelist_path, 'w')
edgelist_fp.write(f'subject{rec_sep}predicate{rec_sep}object\n')

node_metadata_fp = open(node_metadata_path, 'w')
node_metadata_fp.write(f'node_id{rec_sep}node_namespace{rec_sep}node_label{rec_sep}node_definition{rec_sep}node_synonyms{rec_sep}node_dbxrefs\n')

relations_fp = open(relations_path, 'w')
relations_fp.write(f'relation_id{rec_sep}relation_namespace{rec_sep}relation_label{rec_sep}relation_definition\n')
write_relations_file(relations_fp)

line_no = 1
# This should be the header...
line = input_tsv_fp.readline().rstrip()
rec_sep_in_record = line.count(rec_sep)
print(f"Fields in record: {rec_sep_in_record+1}")

eof = False
while not eof:
    line_no += 1
    line = input_tsv_fp.readline().rstrip()

    # if line is empty end of file is reached
    if not line:
        break

    entry, gene, proteins = parse_line(line)
    
    if gene is None or gene == '':
        continue

    write_node_metadata(node_metadata_fp, entry, entry, 'None')
    write_node_metadata(node_metadata_fp, gene, gene, 'Gene name (primary)')
    next_proteins_id_str: str = protein_metadata_node_id(node_metadata_fp, proteins)
    write_edges(edgelist_fp, entry, gene, next_proteins_id_str)

input_tsv_fp.close()

edgelist_fp.close()
node_metadata_fp.close()
relations_fp.close()

elapsed_time = time.time() - start_time
print(f'Done! Lines processed: {line_no}; Elapsed time: {"{:0>8}".format(str(timedelta(seconds=elapsed_time)))}')
