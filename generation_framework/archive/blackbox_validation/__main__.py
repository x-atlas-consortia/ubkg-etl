#!/usr/bin/env python

import argparse
import glob
import logging.config
import time
from datetime import timedelta
from lxml import etree


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


# https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(description='Blackbox test newly generated .csv files.\n'
                                             'In general you should not have the change any of the optional arguments',
                                 formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument('owl_url', type=str, help='url for the OWL file used in the process')
parser.add_argument("-o", "--csv_original", type=str, default='../neo4j/import',
                    help='directory containing the original .csv files')
parser.add_argument("-n", "--csv_new", type=str, default='./csv_output',
                    help='directory containing the newly created .csv files')
parser.add_argument("-l", "--owlnets", type=str, default='./owlnets_output',
                    help='directory containing the owlnets files')
args = parser.parse_args()

csv_original_dir = args.csv_original
csv_new_dir = args.csv_new
owlnets_dir = args.owlnets
uri = args.owl_url

log_dir, log, log_config = 'builds/logs', 'pkt_build_log.log', glob.glob('**/logging.ini', recursive=True)
logger = logging.getLogger(__name__)
logging.config.fileConfig(log_config[0], disable_existing_loggers=False, defaults={'log_file': log_dir + '/' + log})

# Should be read from the source file via the 'xmlns' property....
xmlns_xmlns: str = 'http://purl.obolibrary.org/obo/uberon/ext.owl#'
owl_xmlns: str = 'http://www.w3.org/2002/07/owl#'
cl_xmlns: str = 'http://purl.obolibrary.org/obo/cl#'
rdf_xmlns: str = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
oboInOwl: str = 'http://www.geneontology.org/formats/oboInOwl#'


def file_from_uri(uri_str: str) -> str:
    if uri_str.find('/'):
        return uri_str.rsplit('/', 1)[1]


def xmlns_for_cl(tree: etree.ElementTree, cl: str) -> str:
    print(tree.getroot().attrib)
    return tree.getroot().get(f"{{{xmlns_xmlns}}}{cl}")


def scan_xml_tree_for_imports(tree: etree.ElementTree) -> list:
    # https://docs.python.org/3/library/xml.etree.elementtree.html#parsing-xml-with-namespaces
    imports: list = tree.findall('owl:Ontology/owl:imports', namespaces={'owl': owl_xmlns})
    resource_uris: list = []
    for i in imports:
        resource_uri: str = i.get(f"{{{rdf_xmlns}}}resource")
        resource_uris.append(resource_uri)
    return resource_uris


def scan_xml_tree_for_class_with_oboInOwl_id_cl(tree: etree.ElementTree, cl: str) -> list:
    cl_uc: str = cl.upper()
    ids: list = tree.findall('owl:Class/oboInOwl:id', namespaces={'owl': owl_xmlns, 'oboInOwl': oboInOwl})
    cl_ids: list = []
    for id in ids:
        id_text: str = id.text
        ontology_id: list = id_text.split(':', 1)
        if len(ontology_id) == 2:
            ontology: str = ontology_id[0].upper()
            if ontology == cl_uc:
                cl_ids.append(ontology_id[1])
        else:
            raise Exception(f"Class id should be of the form 'cl:id' but was not: {id_text}")
    return cl_ids


def scan_xml_tree_for_class_about_cl(tree: etree.ElementTree, cl: str) -> list:
    cl_uc: str = cl.upper()
    classes: list = tree.findall('owl:Class', namespaces={'owl': owl_xmlns})
    cl_ids: list = []
    for c in classes:
        # https://www.xml.com/pub/a/2001/01/24/rdf.html
        # Resource nodes are the subjects and objects of statements, and they usually have an rdf:about attribute
        # on them giving the URI of the resource they represent.
        # Also have about: owl:AnnotationProperty, owl:ObjectProperty.
        about: str = c.get(f"{{{rdf_xmlns}}}about")
        if about is not None:
            file: str = file_from_uri(about)
            ontology_id: list = file.split('_', 1)
            if len(ontology_id) == 2:
                ontology: str = ontology_id[0].upper()
                if ontology == cl_uc:
                    cl_ids.append(ontology_id[1])
    return cl_ids


start_time = time.time()

logger.info(f"Processing '{uri}'")

# Read the xml to determine if it contains any imports
# graph = Graph().parse(uri, format='xml')

tree: etree.ElementTree = etree.parse(uri)

# print(xmlns_for_cl(tree, 'cl'))
# exit()

imports: list = scan_xml_tree_for_imports(tree)
if len(imports) != 0:
    logger.info(f"Found the following imports: {', '.join(imports)}")
else:
    logger.info("No imports were found")

class_to_find: str = 'cl'

cl_ids: list = scan_xml_tree_for_class_with_oboInOwl_id_cl(tree, class_to_find)
if len(cl_ids) != 0:
    logger.info(f"Found {len(cl_ids)} of instances of owl:Class/oboInOwl:id {class_to_find.upper()}")
else:
    logger.info(f"No instances of class {class_to_find.upper()} were found")

cl_ids: list = scan_xml_tree_for_class_about_cl(tree, class_to_find)
if len(cl_ids) != 0:
    logger.info(f"Found {len(cl_ids)} instances owl:Class attribute rdf:about {class_to_find.upper()}")
else:
    logger.info(f"No instances owl:Class attribute rdf:about {class_to_find.upper()} were found")

# Add log entry for how long it took to do the processing...
elapsed_time = time.time() - start_time
logger.info('Done! Elapsed time %s', "{:0>8}".format(str(timedelta(seconds=elapsed_time))))
