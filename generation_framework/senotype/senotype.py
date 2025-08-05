#!/usr/bin/env python
# coding: utf-8

# AUGUST 2025

# Senotype library ingestion
# Ingests a set of Senotype specifications.
# Each specification is stored as a JSON file in an online repository, such as a Google drive.

# Ingestion involves
# 1. reading the set of JSON files and consolidating edge and node information into
#    a UBKG edge and node file
# 2. ingesting the node and edge file

# Note: the -s argument (to skip the build of OWLNETS files) does not apply in this workflow.

import argparse
import sys
import os
import pandas as pd
from tqdm import tqdm
import json
import requests


# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path. (This assumes that this script is being called from build_csv.py.)
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)

# Logging module
import ubkg_logging as ulog
# Config file
import ubkg_config as uconfig
# Calling subprocesses
import ubkg_subprocess as usub
# Extracting files
import ubkg_extract as uextract

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass

def getargs()->argparse.Namespace:
    # Parse command line arguments.
    parser = argparse.ArgumentParser(
        description='Builds OWLNETS files from Senotype source',
        formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")

    return parser.parse_args()

def getsenotypejsons(github_url: str, target_dir: str):
    """
    Downloads a set of Senotype JSON files from the senlib GitHub repository.
    :param target_dir: local directory to which to download
    :param folder_id: Google drive folder id
    """

    os.makedirs(target_dir, exist_ok=True)
    uextract.download_github_directory_content(url=github_url, download_full_path=target_dir)

def write_edgefile(owl_dir: str, owlnets_dir: str):
    """
    Builds an edge file from a collection of JSON files.
    :param owl_dir: location of the collection of JSON files
    :param owlnets_dir: output location
    :return:
    """

    os.makedirs(owlnets_dir, exist_ok=True)
    edgelist_path: str = os.path.join(owlnets_dir, 'OWLNETS_edgelist.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(edgelist_path))

    with open(edgelist_path, 'w') as out:
        out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')

        # Loop through the JSONs in the collection.
        try:
            # Get all entries (files and directories) in the specified path
            all_entries = os.listdir(owl_dir)

            # Filter for only files
            json_files_only = [entry for entry in all_entries if os.path.isfile(os.path.join(owl_dir, entry)) and os.path.splitext(entry)[1]=='.json']
            for file_name in json_files_only :
                file_path = os.path.join(owl_dir, file_name)

                # Parse file to build edge assertions.
                with open(file_path, 'r') as f:
                    data = json.load(f)

                    # subject
                    subject = data.get('senotype')
                    subjcode = subject.get('code')
                    # senotype
                    subject = data.get('senotype')
                    subjcode = subject.get('code')

                    assertions = data.get('assertions')
                    for assertion in tqdm(assertions):
                        # predicate
                        predicate = assertion.get('predicate')
                        if predicate.get('IRI') is None:
                            predicatestring = predicate.get('term')
                        else:
                            predicatestring = predicate.get('IRI')

                        # object
                        objects = assertion.get('objects')
                        for o in objects:
                            objcode = o.get('code')
                            # Write an assertion per unique set of subject, predicate, object
                            out.write(subjcode + '\t' + predicatestring + '\t' + objcode + '\n')

        except FileNotFoundError:
            print(f"Error: Directory not found at '{owl_dir}'")
            exit(1)
        except Exception as e:
            print(f"An error occurred in write_edgefile: {e}")
            exit(1)


def getpmidtitle(pmid: str) -> str:
    """
    Calls the NCBI EUtils REST API to obtain information on a PubMedID.
    :param pmid: PubMed ID
    :return: title of publication
    """
    id = pmid.split(':')[1]
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={id}&retmode=json'
    resp = uextract.getresponsejson(url)
    result = resp.get('result')
    if result is not None:
        result_id = result.get(id)
        return result_id.get('title').strip()

def getrridtitle(rrid:str) -> str:
    """
    Uses the SciCrunch resolver to return information on an RRID
    :param rrid: RRID
    :return: description of resource
    """

    ret = ''
    url = f'https://scicrunch.org/resolver/{rrid}.json'
    resp = uextract.getresponsejson(url)
    hits = resp.get('hits')
    if hits is not None:
        hitshits = hits.get('hits')[0]
        if hitshits is not None:
            ret = hitshits.get('_source').get('item').get('description')
    return ret

def getdataset(id: str, token: str)-> str:
    """Obtains information on a SenNet dataset.
    :param id: SenNet ID
    :token: SenNet Globus token
    """
    url = f'https://entity.api.sennetconsortium.org/entities/{id}'
    ret = ''
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url=url, headers=headers)
    if response.status_code == 200:
        respjson = response.json()
        ret = respjson.get('title')

    return ret

def write_nodefile(owl_dir: str, owlnets_dir: str, token: str):
    """
    Builds a node file of unique nodes from a collection of JSON files.
    :param owl_dir: location of the collection of JSON files
    :param owlnets_dir: output location
    :param token: SenNet group token
    :return:
    """

    listnode = []

    node_metadata_path: str = os.path.join(owlnets_dir, 'OWLNETS_node_metadata.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(node_metadata_path))

    # Loop through the JSONs in the collection.
    try:
        # Get all entries (files and directories) in the specified path
        all_entries = os.listdir(owl_dir)

        # Filter for only files
        json_files_only = [entry for entry in all_entries if
                           os.path.isfile(os.path.join(owl_dir, entry)) and os.path.splitext(entry)[1] == '.json']
        for file_name in json_files_only:
            file_path = os.path.join(owl_dir, file_name)

            # Parse file to build nodes.
            with open(file_path, 'r') as f:
                data = json.load(f)
                # The Senotype node gets the properties of the submitter.
                subject = data.get('senotype')
                node_id = subject.get('code')
                node_namespace = ''
                node_label = subject.get('term','')
                node_definition = ''
                node_synonyms = ''
                node_dbxrefs = ''
                value = ''
                lowerbound = ''
                upperbound = ''
                unit = ''
                submitter = data.get('submitter')
                submitter_name = submitter.get('name')
                submitter_first_name = submitter_name.get('first','')
                submitter_last_name = submitter_name.get('last','')
                submitter_email = submitter.get('email','')
                dictnode = {'node_id': node_id,
                            'node_namespace': node_namespace,
                            'node_label': node_label,
                            'node_definition': node_definition,
                            'node_synonyns': node_synonyms,
                            'node_dbxrefs': node_dbxrefs,
                            'value': value,
                            'lowerbound': lowerbound,
                            'upperbound': upperbound,
                            'unit': unit,
                            'firstname': submitter_first_name,
                            'lastname': submitter_last_name,
                            'email': submitter_email}
                listnode.append(dictnode)

                # Find SENOTYPE nodes in assertions
                assertions = data.get('assertions')
                for assertion in assertions:
                    pred = assertion.get('predicate')
                    predicate = pred.get('IRI')
                    if predicate is None:
                        predicate = pred.get('term')
                    objects = assertion.get('objects')
                    for object in objects:
                        node_id = object.get('code')
                        node_namespace = ''
                        if predicate == 'has_citation':
                            node_label = getpmidtitle(pmid=node_id)
                        elif predicate == 'has_origin':
                            node_label = getrridtitle(rrid=node_id)
                        elif predicate == 'has_dataset':
                            node_label = getdataset(id=node_id, token=token)

                        else:
                            node_label = object.get('term','')
                        node_definition = ''
                        node_synonyms = ''
                        node_dbxrefs = ''
                        # value, lowerbound, upperbound, and unit will only be defined for objects of
                        # has_context assertions
                        value = str(object.get('value',''))
                        lowerbound = str(object.get('lowerbound',''))
                        upperbound = str(object.get('upperbound',''))
                        unit = object.get('unit','')
                        submitter_first_name = ''
                        submitter_last_name = ''
                        submitter_email = ''
                        dictnode = {'node_id': node_id,
                                    'node_namespace': node_namespace,
                                    'node_label': node_label,
                                    'node_definition': node_definition,
                                    'node_synonyns': node_synonyms,
                                    'node_dbxrefs': node_dbxrefs,
                                    'value': value,
                                    'lowerbound': lowerbound,
                                    'upperbound': upperbound,
                                    'unit': unit,
                                    'firstname': submitter_first_name,
                                    'lastname': submitter_last_name,
                                    'email': submitter_email}
                        listnode.append(dictnode)

        dfnode = pd.DataFrame(listnode)
        dfnode = dfnode.drop_duplicates()
        dfnode.to_csv(path_or_buf=node_metadata_path, sep='\t', index=False)

    except FileNotFoundError:
        print(f"Error: Directory not found at '{owl_dir}'")
        exit(1)
    except Exception as e:
        print(f"An error occurred in write_nodefile: {e}")
        exit(1)

# -----------------------------------------
# START

args = getargs()

# Read from config file
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/senotype/senotype.ini')
config = uconfig.ubkgConfigParser(cfgfile)

# Get OWL and OWLNETS directories.
# The config file should contain absolute paths to the directories.
owl_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owl_dir'))
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owlnets_dir'))
github_url = config.get_value(section='URL', key='url')
token= config.get_value(section='token', key='sennet')

if args.skipbuild:
    print('Skipping build of edge and node files.')
else:
    # Download set of Senotype JSON files to OWL directory.
    getsenotypejsons(github_url=github_url, target_dir=owl_dir)
    # Build and write edge and node file.
    write_edgefile(owl_dir=owl_dir, owlnets_dir=owlnets_dir)
    write_nodefile(owl_dir=owl_dir, owlnets_dir=owlnets_dir, token=token)

exit(1)


