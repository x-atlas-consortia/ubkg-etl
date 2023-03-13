#!/usr/bin/env python

import argparse
import os
import pkt_kg as pkt
import psutil
import re

import rdflib.exceptions
from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS
from tqdm import tqdm
import glob
import logging.config
import time
from datetime import timedelta
from lxml import etree
from urllib.request import urlopen
import subprocess
import hashlib
from typing import Dict
import pandas as pd

# JAS Jan 2023 - to handle errors from parsing OWL files in Turtle format
from xml.parsers.expat import ParserCreate, ExpatError, errors

# Setup and running the script...
#
# $ cd scripts
# $ python3 -m venv venv
# $ source venv/bin/activate
# $ python --version
# Python 3.9.5
# $ pip install -r requirements.txt
# $ brew install wget
# $ ./owlnets_script/__main__.py owl_url


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


# https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(
    description='Run PheKnowLator on OWL file (required parameter).\n'
                'Before running check to see if there are imports in the OWL file and exit if so'
                'unless the --with_imports switch is also given.\n'
                '\n'
                'In general you should not have the change any of the optional arguments',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument('owl_url', type=str,
                    help='url for the OWL file to process')
parser.add_argument('owl_sab', type=str,
                    help='directory in --owlnets_dir and --owl_dir to save information from this run')
parser.add_argument("-l", "--owlnets_dir", type=str, default='./owlnets_output',
                    help='directory used for the owlnets output files')
parser.add_argument("-o", "--owl_dir", type=str, default='./owl',
                    help='directory used for the owl input files')
parser.add_argument("-t", "--owltools_dir", type=str, default='./pkt_kg/libs',
                    help='directory where the owltools executable is downloaded to')
parser.add_argument("-c", "--clean", action="store_true",
                    help='clean the owlnets_output directory of previous output files before run')
parser.add_argument("-d", "--force_owl_download", action="store_true",
                    help='force downloading of the .owl file before processing')
parser.add_argument("-i", "--ignore_owl_md5", action="store_true",
                    help='ignore differences between .owl MD5 and saved MD5')
parser.add_argument("-w", "--with_imports", action="store_true",
                    help='process OWL file even if imports are found, otherwise give up with an error')
parser.add_argument("-D", "--delete_definitions", action="store_true",
                    help='delete the definitions column when writing files')
parser.add_argument("-r", "--robot", action="store_true",
                    help='apply robot to owl_url incorporating the includes and exit')
parser.add_argument("-v", "--verbose", action="store_true",
                    help='increase output verbosity')
args = parser.parse_args()

log_dir, log, log_config = 'builds/logs', 'pkt_build_log.log', glob.glob('**/logging.ini', recursive=True)
logger = logging.getLogger(__name__)
logging.config.fileConfig(log_config[0], disable_existing_loggers=False, defaults={'log_file': log_dir + '/' + log})

uri = args.owl_url


def print_and_logger_info(message: str) -> None:
    print(message)
    logger.info(message)


def print_and_logger_error(message: str) -> None:
    print(message)
    logger.error(message)


def file_from_uri(uri_str: str) -> str:
    if uri_str.find('/'):
        return uri_str.rsplit('/', 1)[1]


def file_from_path(path_str: str) -> str:
    i = path_str.rfind(os.sep)
    if i > 0 & i < len(path_str)-1:
        return path_str[i+1:]
    return None


def download_owltools(loc: str) -> None:
    owl_tools_url = 'https://github.com/callahantiff/PheKnowLator/raw/master/pkt_kg/libs/owltools'

    cmd = os.system(f"ls {loc}{os.sep}owltools > /dev/null 2>&1")
    if os.WEXITSTATUS(cmd) != 0:
        logger.info('Download owltools and update permissions')
        # move into pkt_kg/libs/ directory
        cwd: src = os.getcwd()

        os.system(f"mkdir -p {loc}")
        os.chdir(loc)

        os.system(f'wget {owl_tools_url}')
        os.system('chmod +x owltools')

        # move back to the working directory
        os.chdir(cwd)


def download_owl(url: str, loc: str, working_file: str, force_empty=True) -> None:
    logger.info(f'Downloading owl file from \'{url}\' to \'{loc}\'')

    cwd: str = os.getcwd()

    os.system(f"mkdir -p {loc}")
    os.chdir(loc)

    if force_empty is True:
        os.system(f"rm -f *.owl *.md5")

    # TODO: This hangs sometimes, so there should be a timeout...
    wgetResults: bytes = subprocess.check_output([f'wget {url}'], shell=True, stderr=subprocess.STDOUT)
    wgetResults_str: str = wgetResults.decode('utf-8')
    for line in wgetResults_str.strip().split('\n'):
        if 'Length: unspecified' in line:
            logger.error(f'Failed to download {uri}')
            print(f'Failed to download {uri}')
            print(wgetResults_str)
            exit(1)
    if args.verbose:
        print(wgetResults_str)

    md5: str = hashlib.md5(open(working_file, 'rb').read()).hexdigest()
    md5_file: str = f'{working_file}.md5'
    logger.info('MD5 for owl file {md5} saved to {md5_file}')
    with open(md5_file, 'w', newline='') as fp:
        fp.write(md5)

    os.chdir(cwd)


def compare_file_md5(working_file: str) -> bool:
    if not os.path.isfile(working_file):
        return False
    md5_file: str = f'{working_file}.md5'
    if not os.path.isfile(md5_file):
        return False
    with open(md5_file, 'r', newline='') as fp:
        saved_md5 = fp.read()
        md5: str = hashlib.md5(open(working_file, 'rb').read()).hexdigest()
        if md5 == saved_md5:
            return True
    return False


# https://docs.python.org/3/library/xml.etree.elementtree.html#parsing-xml-with-namespaces
def scan_xml_tree_for_imports(tree: etree.ElementTree) -> list:
    # These should be read from the source file via the 'xmlns' property....
    owl_xmlns: str = 'http://www.w3.org/2002/07/owl#'
    rdf_xmlns: str = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'

    imports: list = tree.findall('owl:Ontology/owl:imports', namespaces={'owl': owl_xmlns})
    resource_uris: list = []
    for i in imports:
        resource_uri: str = i.get(f"{{{rdf_xmlns}}}resource")
        resource_uris.append(resource_uri)
    return resource_uris


def search_owl_file_for_imports(owl_filename: str) -> None:
    parser = etree.HTMLParser()
    tree: etree.ElementTree = etree.parse(owl_filename, parser)
    imports: list = scan_xml_tree_for_imports(tree)
    if len(imports) != 0:
        logger.info(f"Found the following imports were found in the OWL file {uri} : {', '.join(imports)}")
        if args.with_imports is not True:
            print_and_logger_info(f"Imports found in OWL file {uri}. Exiting")
            exit(1)
    else:
        print_and_logger_info(f"No imports were found in OWL file {uri}")


def log_files_and_sizes(dir: str) -> None:
    for file in os.listdir(dir):
        generated_file: str = os.path.join(dir, file)
        size: int = os.path.getsize(generated_file)
        logger.info(f"Generated file '{generated_file}' size {size:,}")


def look_for_none_in_node_metadata_file(dir: str) -> None:
    file: str = dir + os.path.sep + 'OWLNETS_node_metadata.txt'
    print(f'Searching {file}')
    data = pd.read_csv(file, sep='\t')

    # TODO: We will potentially find ontologies without synonyms.
    message: str = f"Total columns in {file}: {len(data['node_synonyms'])}"
    print_and_logger_info(message)
    node_synonyms_not_None = data[data['node_synonyms'].str.contains('None')==False]
    message: str = f"Columns in {file} where node_synonyms is not None: {len(node_synonyms_not_None)}"
    print_and_logger_info(message)
    node_dbxrefs_not_None = data[data['node_dbxrefs'].str.contains('None')==False]
    message: str = f"Columns in {file} where node_dbxrefs is not None: {len(node_dbxrefs_not_None)}"
    print_and_logger_info(message)
    both_not_None = node_synonyms_not_None[node_synonyms_not_None['node_dbxrefs'].str.contains('None')==False]
    print(f"Columns where node_synonyms && node_dbxrefs is not None: {len(both_not_None)}")


def robot_merge(owl_url: str) -> None:
    logger.info(f"Running robot merge on '{uri}'")
    loc = f'.{os.sep}robot'
    robot_jar = 'https://github.com/ontodev/robot/releases/download/v1.8.1/robot.jar'
    robot_sh = 'https://raw.githubusercontent.com/ontodev/robot/master/bin/robot'

    if 'JAVA_HOME' not in os.environ:
        print('The environment variable JAVA_HOME must be set and point to a valid JDK')
        exit(1)
    java_home: str = os.getenv('JAVA_HOME')
    jdk: str = file_from_path(java_home)
    if not re.match(r'^jdk-.*\.jdk$', jdk):
        print_and_logger_info(f'Environment variable JAVA_HOME={java_home} does not appear to point to a valid JDK?')
        exit(1)

    cwd = os.getcwd()
    os.system(f"mkdir -p {loc}")
    os.chdir(loc)

    if not os.path.exists(file_from_uri(robot_jar)):
        os.system(f"wget {robot_jar}")

    robot: str = file_from_uri(robot_sh)
    if not os.path.exists(robot):
        os.system(f"wget {robot_sh}")
        os.system(f"chmod +x {robot}")

    owl_file: str = file_from_uri(owl_url)
    if not os.path.exists(owl_file):
        os.system(f"wget {owl_url}")

    # https://robot.obolibrary.org/merge
    os.system(f".{os.sep}robot merge --input .{os.sep}{owl_file} --output .{os.sep}{owl_file}.merge")

    # move back to the working directory
    os.chdir(cwd)


if args.verbose is True:
    print('Parameters:')
    print(f" * Verbose mode")
    if args.clean is True:
        print(" * Cleaning owlnets directory")
    print(f" * Owl URL: {args.owl_url}")
    print(f" * Owl sab: {args.owl_sab}")
    print(f" * Owlnets directory: {args.owlnets_dir} (exists: {os.path.isdir(args.owlnets_dir)})")
    print(f" * Owltools directory: {args.owltools_dir} (exists: {os.path.isdir(args.owltools_dir)})")
    print(f" * Owl directory: {args.owl_dir} (exists: {os.path.isdir(args.owl_dir)})")
    if args.force_owl_download is True:
        print(f" * PheKnowLator will force .owl file downloads")
    if args.with_imports is True:
        print(f" * PheKnowLator will run even if imports are found in .owl file")
    if args.delete_definitions is True:
        print(f" * Delete definitions column in the output .txt files")
    print('')

start_time = time.time()

print(f"Processing '{uri}'")
logger.info(f"Processing '{uri}'")

# This should remove imports if any. Currently it's a one shot deal and exits.
# TODO: In the future the output of this can be fed into the pipeline so that the processing contains no imports.
if args.robot is True:
    robot_merge(uri)
    elapsed_time = time.time() - start_time
    print_and_logger_info('Done! Elapsed time %s', "{:0>8}".format(str(timedelta(seconds=elapsed_time))))
    exit(0)

download_owltools(args.owltools_dir)

working_dir: str = os.path.join(args.owlnets_dir, args.owl_sab)
logger.info("Make sure working directory '%s' exists", working_dir)
os.system(f"mkdir -p {working_dir}")

if args.clean is True:
    msg: str = f"Deleting OWLNETS files in working directory {working_dir}"
    logger.info(msg)
    if args.verbose:
        print(msg)
    os.system(f"cd {working_dir}; rm -f *")
    working_dir_file_list = os.listdir(working_dir)
    if len(working_dir_file_list) == 0:
        logger.info(f"Working directory {working_dir} is empty")
    else:
        logger.error(f"Working directory {working_dir} is NOT empty")


# Code below taken from:
# https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb


logger.info('Loading ontology')
# ALWAYS parse a local copy of the .owl file (uri).
# NOTE: Sometimes, with large documents (eg., chebi) the uri parse hangs, so here we download the document first
# Another problem is with chebi, there is a redirect which Graph.parse(uri, ...) may not handle.
owl_dir: str = os.path.join(args.owl_dir, args.owl_sab)
working_file: str = file_from_uri(uri)
owl_file: str = os.path.join(owl_dir, working_file)

if args.force_owl_download is True or os.path.exists(owl_file) is False:
    if args.verbose:
        print_and_logger_info(f"Downloading .owl file to {owl_file} (force .owl download specified)")
    download_owl(uri, owl_dir, working_file)
elif args.ignore_owl_md5 is True:
    if args.verbose:
        print_and_logger_info(f"Ignoring .owl file {owl_file} MD5")
elif compare_file_md5(owl_file) is False:
    if args.verbose:
        print_and_logger_info(f"Downloading .owl file to {owl_file} (MD5 of .owl file does not match)")
    download_owl(uri, owl_dir, working_file)

if args.verbose:
    print_and_logger_info(f"Using .owl file at {owl_file}")

search_owl_file_for_imports(owl_file)

# JAS January 2023
# The original logic assumed that OWL files were in RDF/XML format. Almost all of the OWL files that have been
# encountered up to January 2023 have been in RDF/XML. (The exception is GlycoRDF, which is available in both
# RDF/XML and OWL/XML serializations.)
#
# Some ontologies are available only in non-RDF/XML serializations. For example, GlycoCoO is only available in Turtle.
# Attempt to parse in Turtle; serialize to RDF/XML; and then reparse the RDF/XML.
try:
    graph = Graph().parse(owl_file, format='xml')
except:
    # Note: If the file is not in RDF/XML, the exception will be from xml (ExpatError), not rdflib.
    # Exception handling does not seem able to catch this lower-level error, so this logic uses the generic
    # exception handler.

    # This logic does not handle the use case of an input file being in some format other than RDF/XML or Turtle--
    # in particular, if the file is OWL/RDF.
    # It is assumed that such a case would be properly addressed--i.e., either don't use the file as input or
    # modify this logic further to account for the other formats.

    print_and_logger_info(f'Error parsing {owl_file}. The file may not be in RDF/XML format. Assuming Turtle format. Attempting to convert...')
    graph = Graph().parse(owl_file, format='n3')
    convertedpath = os.path.join(owl_dir,'converted.owl')
    print_and_logger_info(f'Serializing {owl_file} to RDF/XML format in file {convertedpath}')
    v = graph.serialize(format='xml', destination=convertedpath)
    graph2 = Graph().parse(convertedpath, format='xml')
    graph = graph2

logger.info('Extract Node Metadata')
ont_classes = pkt.utils.gets_ontology_classes(graph)
ont_labels = {str(x[0]): str(x[2]) for x in list(graph.triples((None, RDFS.label, None)))}
ont_synonyms = pkt.utils.gets_ontology_class_synonyms(graph)
ont_dbxrefs = pkt.utils.gets_ontology_class_dbxrefs(graph)
ont_defs = pkt.utils.gets_ontology_definitions(graph)

logger.info('Add the class metadata to the master metadata dictionary')
entity_metadata = {'nodes': {}, 'relations': {}}
for cls in tqdm(ont_classes):
    # get class metadata - synonyms and dbxrefs
    syns = '|'.join([k for k, v in ont_synonyms[0].items() if str(cls) in v])
    dbxrefs = '|'.join([k for k, v in ont_dbxrefs[0].items() if str(cls) in v])

    # extract metadata
    cls_path_last: str = str(cls).split('/')[-1]
    if '_' in cls_path_last:
        namespace_candidate = re.findall(r'^(.*?)(?=\W|_)', cls_path_last)
        if len(namespace_candidate) > 0:
            namespace: str = namespace_candidate[0].upper()
    else:
        namespace: str = str(cls).split('/')[2]

    # update dict
    # TODO: 'namespace' can be undefined...
    entity_metadata['nodes'][str(cls)] = {
        'label': ont_labels[str(cls)] if str(cls) in ont_labels.keys() else 'None',
        'synonyms': syns if syns != '' else 'None',
        'dbxrefs': dbxrefs if dbxrefs != '' else 'None',
        'namespace': namespace,
        'definitions': str(ont_defs[cls]) if cls in ont_defs.keys() else 'None',
    }

ont_objects = pkt.utils.gets_object_properties(graph)
logger.info('Add the object metadata to the master metadata dictionary')
for obj in tqdm(ont_objects):
    # get object label
    label_hits = list(graph.objects(obj, RDFS.label))
    label = str(label_hits[0]) if len(label_hits) > 0 else 'None'

    # get object namespace
    if 'obo' in str(obj) and len(str(obj).split('/')) > 5:
        namespace = str(obj).split('/')[-2].upper()
    else:
        if '_' in str(obj): namespace = re.findall(r'^(.*?)(?=\W|_)', str(obj).split('/')[-1])[0].upper()
        else: namespace = str(obj).split('/')[2]

    # update dict
    entity_metadata['relations'][str(obj)] = {'label': label, 'namespace': namespace,
                                             'definitions': str(ont_defs[obj]) if obj in ont_defs.keys() else 'None'}

logger.info('Add RDF:type and RDFS:subclassOf')
entity_metadata['relations']['http://www.w3.org/2000/01/rdf-schema#subClassOf'] =\
    {'label': 'subClassOf', 'definitions': 'None', 'namespace': 'www.w3.org'}
entity_metadata['relations']['http://www.w3.org/1999/02/22-rdf-syntax-ns#type'] =\
    {'label': 'type', 'definitions': 'None', 'namespace': 'www.w3.org'}

print_and_logger_info('Stats for original graph before running OWL-NETS')
pkt.utils.derives_graph_statistics(graph)

logger.info('Initialize owlnets class')
# graph: An RDFLib object or a list of RDFLib Graph objects.
# write_location: A file path used for writing knowledge graph data (e.g. "resources/".
# filename: A string containing the filename for the full knowledge graph (e.g. "/hpo_owlnets").
# kg_construct_approach: A string containing the type of construction approach used to build the knowledge graph.
# owl_tools: A string pointing to the location of the owl tools library.
# top_level: A list of ontology namespaces that should not appear in any or in the clean graph.
# support: A list of ontology namespaces that should not appear in any or in the clean graph.
# relations: A list of ontology namespaces that should not appear in any or in the clean graph.
owlnets = pkt.OwlNets(graph=graph,
                      write_location=working_dir + os.sep,
                      filename=file_from_uri(uri),
                      kg_construct_approach=None,
                      owl_tools=args.owltools_dir + os.sep + 'owltools',
                      # top_level=['ISO', 'SUMO', 'BFO'],
                      # support=['IAO', 'SWO', 'OBI', 'UBPROP'],
                      # relations=['RO'],
                      top_level=['ISO', 'SUMO', 'BFO'],
                      support=['IAO', 'SWO', 'UBPROP'],
                      relations=['RO']
                      )

print_and_logger_info('Remove disjointness with Axioms')
owlnets.removes_disjoint_with_axioms()

print_and_logger_info('Remove triples used only to support semantics')
cleaned_graph = owlnets.removes_edges_with_owl_semantics()
filtered_triple_count = len(owlnets.owl_nets_dict['filtered_triples'])
logger.info('removed {} triples that were not biologically meaningful'.format(filtered_triple_count))

print_and_logger_info('Gather list of owl:Class and owl:Axiom entities')
owl_classes = list(pkt.utils.gets_ontology_classes(owlnets.graph))
owl_axioms: list = []
for x in tqdm(set(owlnets.graph.subjects(RDF.type, OWL.Axiom))):
    src = set(owlnets.graph.objects(list(owlnets.graph.objects(x, OWL.annotatedSource))[0], RDF.type))
    tgt = set(owlnets.graph.objects(list(owlnets.graph.objects(x, OWL.annotatedTarget))[0], RDF.type))
    if OWL.Class in src and OWL.Class in tgt: owl_axioms += [x]
    elif (OWL.Class in src and len(tgt) == 0) or (OWL.Class in tgt and len(src) == 0): owl_axioms += [x]
    else: pass
node_list = list(set(owl_classes) | set(owl_axioms))
logger.info('There are:\n-{} OWL:Class objects\n-{} OWL:Axiom Objects'. format(len(owl_classes), len(owl_axioms)))

print_and_logger_info('Decode owl semantics')
owlnets.cleans_owl_encoded_entities(node_list)
decoded_graph: Dict = owlnets.gets_owlnets_graph()

print_and_logger_info('Update graph to get all cleaned edges')
owlnets.graph: Dict = cleaned_graph + decoded_graph

str1 = 'Decoded {} owl-encoded classes and axioms. Note the following:\nPartially processed {} cardinality ' \
               'elements\nRemoved {} owl:disjointWith axioms\nIgnored:\n  -{} misc classes;\n  -{} classes constructed with ' \
               'owl:complementOf;\n  -{} classes containing negation (e.g. pr#lacks_part, cl#has_not_completed)\n' \
               '\nFiltering removed {} semantic support triples'
stats_str = str1.format(
    len(owlnets.owl_nets_dict['decoded_entities'].keys()), len(owlnets.owl_nets_dict['cardinality'].keys()),
    len(owlnets.owl_nets_dict['disjointWith']), len(owlnets.owl_nets_dict['misc'].keys()),
    len(owlnets.owl_nets_dict['complementOf'].keys()), len(owlnets.owl_nets_dict['negation'].keys()),
    len(owlnets.owl_nets_dict['filtered_triples']))
print_and_logger_info(f'Print OWL-NETS results: {stats_str}')

# run line below if you want to ensure resulting graph contains
# common_ancestor = 'http://purl.obolibrary.org/obo/BFO_0000001'
# owlnets.graph = owlnets.makes_graph_connected(owlnets.graph, common_ancestor)

print_and_logger_info(f"Writing owl-nets results files to directory '{working_dir}'")
owlnets.write_location = working_dir
owlnets.write_out_results(owlnets.graph)

edge_list_filename: str = working_dir + os.sep + 'OWLNETS_edgelist.txt'
print_and_logger_info(f"Write edge list results to '{edge_list_filename}'")
with open(edge_list_filename, 'w') as out:
    out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')
    for row in tqdm(owlnets.graph):
        out.write(str(row[0]) + '\t' + str(row[1]) + '\t' + str(row[2]) + '\n')

print_and_logger_info('Get all unique nodes in OWL-NETS graph')
nodes = set([x for y in [[str(x[0]), str(x[2])] for x in owlnets.graph] for x in y])

node_metadata_filename: str = working_dir + os.sep + 'OWLNETS_node_metadata.txt'
print_and_logger_info(f"Write node metadata results to '{node_metadata_filename}'")
with open(node_metadata_filename, 'w') as out:
    if args.delete_definitions is True:
        out.write('node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' +
                  'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')
    else:
        out.write('node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' +
                  'node_definition' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')
    for x in tqdm(nodes):
        if x in entity_metadata['nodes'].keys():
            namespace = entity_metadata['nodes'][x]['namespace']
            labels = entity_metadata['nodes'][x]['label']
            definitions = entity_metadata['nodes'][x]['definitions']
            synonyms = entity_metadata['nodes'][x]['synonyms']
            dbxrefs = entity_metadata['nodes'][x]['dbxrefs']
            if args.delete_definitions is True:
                out.write(x + '\t' + namespace + '\t' + labels + '\t' + synonyms + '\t' + dbxrefs + '\n')
            else:
                out.write(x + '\t' + namespace + '\t' + labels + '\t' + definitions + '\t' + synonyms + '\t' + dbxrefs + '\n')

print_and_logger_info('Get all unique nodes in OWL-NETS graph')
relations = set([str(x[1]) for x in owlnets.graph])

relation_filename: str = working_dir + os.sep + 'OWLNETS_relations.txt'
print_and_logger_info(f"Writing relation metadata results to '{relation_filename}'")
with open(relation_filename, 'w') as out:
    if args.delete_definitions is True:
        out.write('relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\n')
    else:
        out.write('relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\t' + 'relation_definition' + '\n')
    for x in tqdm(relations):
        if x in entity_metadata['relations']:
            if 'namespace' in entity_metadata['relations'][x]:
                namespace = entity_metadata['relations'][x]['namespace']
                if 'label' in entity_metadata['relations'][x]:
                    label = entity_metadata['relations'][x]['label']
                    if 'definitions' in entity_metadata['relations'][x]:
                        definitions = entity_metadata['relations'][x]['definitions']
                        if args.delete_definitions is True:
                            out.write(x + '\t' + namespace + '\t' + label + '\n')
                        else:
                            out.write(x + '\t' + namespace + '\t' + label + '\t' + definitions + '\n')
                    else:
                        print_and_logger_error(f"entity_metadata['relations'][{x}]['definitions'] not found in: {entity_metadata['relations'][x]}")
                else:
                    print_and_logger_error(f"entity_metadata['relations'][{x}]['label'] not found in: {entity_metadata['relations'][x]}")
            else:
                print_and_logger_error(f"entity_metadata['relations'][{x}]['namespace'] not found in: {entity_metadata['relations'][x]}")
        else:
            print_and_logger_error(f"entity_metadata['relations'][{x}] not found in: {entity_metadata['relations']}")

log_files_and_sizes(working_dir)
look_for_none_in_node_metadata_file(working_dir)

# Add log entry for how long it took to do the processing...
elapsed_time = time.time() - start_time
print_and_logger_info(f'Done! Elapsed time {"{:0>8}".format(str(timedelta(seconds=elapsed_time)))}')
