#!/usr/bin/env python

import argparse
import os
import pkt_kg as pkt
import psutil
import re
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
                    help='url for the OWL file to process.')
parser.add_argument("-l", "--owlnets_dir", type=str, default='./owlnets_output',
                    help='directory used for the owlnets output files')
parser.add_argument("-t", "--owltools_dir", type=str, default='./pkt_kg/libs',
                    help='directory where the owltools executable is downloaded to')
parser.add_argument("-o", "--owl_dir", type=str, default='./owl',
                    help='directory used for the owl input files')
parser.add_argument("-c", "--clean", action="store_true",
                    help='clean the owlnets_output directory of previous output files before run')
parser.add_argument("-d", "--force_owl_download", action="store_true",
                    help='force downloading of the .owl file before processing')
parser.add_argument("-w", "--with_imports", action="store_true",
                    help='process OWL file even if imports are found, otherwise give up with an error')
parser.add_argument("-r", "--robot", action="store_true",
                    help='apply robot to owl_url incorporating the includes and exit')
parser.add_argument("-v", "--verbose", action="store_true",
                    help='increase output verbosity')
args = parser.parse_args()

log_dir, log, log_config = 'builds/logs', 'pkt_build_log.log', glob.glob('**/logging.ini', recursive=True)
logger = logging.getLogger(__name__)
logging.config.fileConfig(log_config[0], disable_existing_loggers=False, defaults={'log_file': log_dir + '/' + log})

uri = args.owl_url


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

    cmd = os.system(f"ls {loc}{os.sep}owltools")
    if os.WEXITSTATUS(cmd) != 0:
        logger.info('Download owltools and update permissions')
        # move into pkt_kg/libs/ directory
        cwd = os.getcwd()
        os.system(f"mkdir -p {loc}")
        os.chdir(loc)

        os.system(f'wget {owl_tools_url}')
        os.system('chmod +x owltools')

        # move back to the working directory
        os.chdir(cwd)


def download_owl(url: str, loc: str, force_empty=True) -> str:
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
            exit_msg = f"Imports found in OWL file {uri}. Exiting"
            logger.info(exit_msg)
            print(exit_msg)
            exit(1)
    else:
        msg = f"No imports were found in OWL file {uri}"
        logger.info(msg)
        if args.verbose:
            print(msg)


def log_files_and_sizes(dir: str) -> None:
    for file in os.listdir(dir):
        generated_file: str = os.path.join(dir, file)
        size: int = os.path.getsize(generated_file)
        logger.info(f"Generated file '{generated_file}' size {size:,}")


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
        print(f'Environment variable JAVA_HOME={java_home} does not appear to point to a valid JDK?')
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


start_time = time.time()

print(f"Processing '{uri}'")
logger.info(f"Processing '{uri}'")

# This should remove imports if any. Currently it's a one shot deal and exits.
# TODO: In the future the output of this can be fed into the pipeline so that the processing contains no imports.
if args.robot is True:
    robot_merge(uri)
    elapsed_time = time.time() - start_time
    logger.info('Done! Elapsed time %s', "{:0>8}".format(str(timedelta(seconds=elapsed_time))))
    exit(0)

download_owltools(args.owltools_dir)

working_file: str = file_from_uri(uri)
uri_dir: str = working_file.rsplit('.', 1)[0]

working_dir: str = args.owlnets_dir + os.path.sep + uri_dir
logger.info("Make sure working directory '%s' exists", working_dir)
os.system(f"mkdir -p {working_dir}")

if args.clean is True:
    logger.info(f"Deleting files in working directory {working_dir} because of --clean option")
    os.system(f"cd {working_dir}; rm -f *")
    working_dir_file_list = os.listdir(working_dir)
    if len(working_dir_file_list) == 0:
        logger.info(f"Working directory {working_dir} is empty")
    else:
        logger.error(f"Working directory {working_dir} is NOT empty")


# Code below taken from:
# https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb

cpus = psutil.cpu_count(logical=True)

logger.info('Loading ontology')
# Parse an XML document from a URL or an InputSource.
# NOTE: Sometimes, with large documents (eg., chebi) the uri parse hangs, so here we download the document first
# Another problem is with chebi, there is a redirect which Graph.parse(uri, ...) may not handle.
parse_loc: str = uri
owl_dir: str = args.owl_dir + os.path.sep + uri_dir
owl_file: str = owl_dir + os.path.sep + working_file

if compare_file_md5(owl_file) is False or args.force_owl_download is True:
    download_owl(uri, owl_dir)
# At this point we have either downloaded the .owl file because the MD5 that we found for it was wrong,
# or we were told to force the download. If the MD5 is wrong at this point, we punt!
if compare_file_md5(owl_file) is False:
    err_msg: str = f"MD5 for OWL file does not match?! Terminating."
    logger.error(err_msg)
    print(err_msg)
    exit(1)

search_owl_file_for_imports(owl_file)

graph = Graph().parse(parse_loc, format='xml')

logger.info('Extract Node Metadata')
ont_classes = pkt.utils.gets_ontology_classes(graph)
ont_labels = {str(x[0]): str(x[2]) for x in list(graph.triples((None, RDFS.label, None)))}
ont_synonyms = pkt.utils.gets_ontology_class_synonyms(graph)
ont_dbxrefs = pkt.utils.gets_ontology_class_dbxrefs(graph)
ont_objects = pkt.utils.gets_object_properties(graph)

logger.info('Add the class metadata to the master metadata dictionary')
entity_metadata = {'nodes': {}, 'relations': {}}
for cls in tqdm(ont_classes):
    # get class metadata - synonyms and dbxrefs
    syns = '|'.join([k for k, v in ont_synonyms[0].items() if v == str(cls)])
    dbxrefs = '|'.join([k for k, v in ont_dbxrefs[0].items() if v == str(cls)])

    # extract metadata
    if '_' in str(cls):
        namespace = re.findall(r'^(.*?)(?=\W|_)', str(cls).split('/')[-1])[0].upper()
    else:
        namespace = str(cls).split('/')[2]

    # update dict
    entity_metadata['nodes'][str(cls)] = {
        'label': ont_labels[str(cls)] if str(cls) in ont_labels.keys() else 'None',
        'synonyms': syns if syns != '' else 'None',
        'dbxrefs': dbxrefs if dbxrefs != '' else 'None',
        'namespace': namespace
    }

logger.info('Add the object metadata to the master metadata dictionary')
for obj in tqdm(ont_objects):
    # get object label
    label_hits = list(graph.objects(obj, RDFS.label))
    label = str(label_hits[0]) if len(label_hits) > 0 else 'None'

    # get object namespace
    if 'obo' in str(obj) and len(str(obj).split('/')) > 5:
        namespace = str(obj).split('/')[-2].upper()
    else:
        if '_' in str(obj):
            namespace = re.findall(r'^(.*?)(?=\W|_)', str(obj).split('/')[-1])[0].upper()
        else:
            namespace = str(obj).split('/')[2]

    # update dict
    entity_metadata['relations'][str(obj)] = {'label': label, 'namespace': namespace}

logger.info('Add RDF:type and RDFS:subclassOf')
entity_metadata['relations']['http://www.w3.org/2000/01/rdf-schema#subClassOf'] =\
    {'label': 'subClassOf', 'namespace': 'www.w3.org'}
entity_metadata['relations']['https://www.w3.org/1999/02/22-rdf-syntax-ns#type'] =\
    {'label': 'type', 'namespace': 'www.w3.org'}

logger.info('Stats for original graph before running OWL-NETS')
pkt.utils.derives_graph_statistics(graph)

logger.info('Initialize owlnets class')
owlnets = pkt.OwlNets(graph=graph,
                      write_location=working_dir + os.sep,
                      filename=file_from_uri(uri),
                      kg_construct_approach=None,
                      owl_tools=args.owltools_dir + os.sep + 'owltools')

logger.info('Remove disjointness with Axioms')
owlnets.removes_disjoint_with_axioms()

logger.info('Remove triples used only to support semantics')
cleaned_graph = owlnets.removes_edges_with_owl_semantics()
filtered_triple_count = len(owlnets.owl_nets_dict['filtered_triples'])
logger.info('removed {} triples that were not biologically meaningful'.format(filtered_triple_count))

logger.info('Gather list of owl:class and owl:axiom entities')
owl_classes = list(pkt.utils.gets_ontology_classes(owlnets.graph))
owl_axioms: list = []
for x in tqdm(set(owlnets.graph.subjects(RDF.type, OWL.Axiom))):
    src = set(owlnets.graph.objects(list(owlnets.graph.objects(x, OWL.annotatedSource))[0], RDF.type))
    tgt = set(owlnets.graph.objects(list(owlnets.graph.objects(x, OWL.annotatedTarget))[0], RDF.type))
    if OWL.Class in src and OWL.Class in tgt:
        owl_axioms += [x]
    elif (OWL.Class in src and len(tgt) == 0) or (OWL.Class in tgt and len(src) == 0):
        owl_axioms += [x]
    else:
        pass
node_list = list(set(owl_classes) | set(owl_axioms))
logger.info('There are:\n-{} OWL:Class objects\n-{} OWL:Axiom Objects'. format(len(owl_classes), len(owl_axioms)))

logger.info('Decode owl semantics')
owlnets.cleans_owl_encoded_entities(node_list)
decoded_graph: Dict = owlnets.gets_owlnets_graph()

logger.info('Update graph to get all cleaned edges')
owlnets.graph = cleaned_graph + decoded_graph

logger.info('Owlnets results')
str1 = 'Decoded {} owl-encoded classes and axioms. Note the following:\nPartially processed {} cardinality ' \
               'elements\nRemoved {} owl:disjointWith axioms\nIgnored:\n  -{} misc classes;\n  -{} classes constructed with ' \
               'owl:complementOf;\n  -{} classes containing negation (e.g. pr#lacks_part, cl#has_not_completed)\n' \
               'Filtering removed {} semantic support triples'
stats_str = str1.format(
    len(owlnets.owl_nets_dict['decoded_entities'].keys()), len(owlnets.owl_nets_dict['cardinality'].keys()),
    len(owlnets.owl_nets_dict['disjointWith']), len(owlnets.owl_nets_dict['misc'].keys()),
    len(owlnets.owl_nets_dict['complementOf'].keys()), len(owlnets.owl_nets_dict['negation'].keys()),
    len(owlnets.owl_nets_dict['filtered_triples']))
logger.info('=' * 80 + '\n' + stats_str + '\n' + '=' * 80)

# common_ancestor = 'http://purl.obolibrary.org/obo/BFO_0000001'
# owlnets.graph = owlnets.makes_graph_connected(owlnets.graph, common_ancestor)

logger.info(f"Writing owl-nets results files to directory '{working_dir}'")
owlnets.write_location = working_dir
owlnets.write_out_results(owlnets.graph)

edge_list_filename: str = working_dir + os.sep + 'OWLNETS_edgelist.txt'
logger.info(f"Write edge list results to '{edge_list_filename}'")
with open(edge_list_filename, 'w') as out:
    out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')
    for row in tqdm(owlnets.graph):
        out.write(str(row[0]) + '\t' + str(row[1]) + '\t' + str(row[2]) + '\n')

logger.info('Get all unique nodes in OWL-NETS graph')
nodes = set([x for y in [[str(x[0]), str(x[2])] for x in owlnets.graph] for x in y])

node_metadata_filename: str = working_dir + os.sep + 'OWLNETS_node_metadata.txt'
logger.info(f"Write node metadata results to '{node_metadata_filename}'")
with open(node_metadata_filename, 'w') as out:
    out.write('node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')
    for x in tqdm(nodes):
        if x in entity_metadata['nodes'].keys():
            namespace = entity_metadata['nodes'][x]['namespace']
            labels = entity_metadata['nodes'][x]['label']
            synonyms = entity_metadata['nodes'][x]['synonyms']
            dbxrefs = entity_metadata['nodes'][x]['dbxrefs']
            out.write(x + '\t' + namespace + '\t' + labels + '\t' + synonyms + '\t' + dbxrefs + '\n')

logger.info('Get all unique nodes in OWL-NETS graph')
relations = set([str(x[1]) for x in owlnets.graph])

relation_filename: str = working_dir + os.sep + 'OWLNETS_relations.txt'
logger.info(f"Writing relation metadata results to '{relation_filename}'")
with open(relation_filename, 'w') as out:
    out.write('relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\n')
    for x in tqdm(relations):
        if x in entity_metadata['relations']:
            if 'namespace' in entity_metadata['relations'][x]:
                namespace = entity_metadata['relations'][x]['namespace']
                if 'label' in entity_metadata['relations'][x]:
                    label = entity_metadata['relations'][x]['label']
                    out.write(x + '\t' + namespace + '\t' + label + '\n')
                else:
                    logger.error(f"entity_metadata['relations'][{x}]['label'] not found in: {entity_metadata['relations'][x]}")
            else:
                logger.error(f"entity_metadata['relations'][{x}]['namespace'] not found in: {entity_metadata['relations'][x]}")
        else:
            logger.error(f"entity_metadata['relations'][{x}] not found in: {entity_metadata['relations']}")

log_files_and_sizes(working_dir)

# Add log entry for how long it took to do the processing...
elapsed_time = time.time() - start_time
logger.info('Done! Elapsed time %s', "{:0>8}".format(str(timedelta(seconds=elapsed_time))))
