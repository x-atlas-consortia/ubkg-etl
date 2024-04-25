#!/usr/bin/env python
"""
hmfields

initial version: November 2023

UBKG ETL that imports metadata for samples ingested in HuBMAP prior to the integration with CEDAR.

Reads and translates YAML files stored in the
https://github.com/hubmapconsortium/ingest-validation-tools/tree/main/docs folder.

"""
import argparse
import yaml
import requests
import sys
import os
import urllib

# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path. (This assumes that this script is being called from build_csv.py.)
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)
# Logging module
import ubkg_logging as ulog
# Config file
import ubkg_config as uconfig

def load_yaml(url: str) -> dict:
    """
    Loads a YAML file with a simple list format.
    :param url: URL to the file
    :return: list[str]
    """

    # Retrieve the file content from the URL
    response = requests.get(url, allow_redirects=True)
    # Convert bytes to string
    content = response.content.decode("utf-8")
    # Load the yaml
    content = yaml.safe_load(content)
    print(url)
    print(content)
    return content


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


def getargs() -> argparse.Namespace:
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description='Builds ontology files in '
                                                 'OWLNETS format from the ingest-validation_tools repo.',
                                     formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("sab", help="SAB for metadata field ontology")
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")
    retargs = parser.parse_args()

    return retargs


def get_node_id(idx: int, sab: str) -> str:
    """
    Builds a node_id based on an index value and SAB.
    :param idx: numeric index
    :param sab: field metadata ontology SAB
    :return: str
    """
    return f'{sab}:{idx:04d}'


def build_parent_node_list(sab: str, dict_index: dict) -> list:
    """
    Builds a list of parent nodes for the HMFIELD ontology.
    :param sab: ingest metadata ontology SAB
    :param dict_index: dict of parent node indexes.
    :return: list of dictionaries of node information
    """

    list_nodes = []
    for parent in dict_index:
        node_id = get_node_id(idx=dict_index[parent], sab=sab)
        node_label = f'{sab} {parent} parent node'
        node_definition = ''
        node_synonyms = ''
        node_dbxrefs = ''
        dict_node = {'node_id': node_id, 'namespace': sab, 'node_label': node_label, 'node_definition': node_definition,
                     'node_synonyms': node_synonyms, 'node_dbxrefs': node_dbxrefs}
        list_nodes.append(dict_node)

    return list_nodes


def build_node_list(sab: str, yaml_dict_field_nodes: dict, parent_node_idx: int, node_type: str, urlbase: str) -> list:
    """
    Build a unique list of encoded, cross-referenced nodes for addition to the nodes file.
    :param sab: SAB for the ingest metadata vocabulary.
    :param yaml_dict_field_nodes: dictionary from one of the ingest metadata YAML files
    :param parent_node_idx: index for parent node in the ontology--i.e., root, field, schema, type
    :param node_type: type of node, used to determine form of cross-reference.
    :param urlbase: base URL for the UBKG API
    :return: list of encoded nodes, with each node in a dict in format
    {'node_id':<node_id>, 'node_label':<either the node term or the key>, 'node_definition':<node definition>,
     'dbxref': <cross-referenced code>}
    """
    ulog.print_and_logger_info(f'Building unique list of encoded and cross-referenced {node_type} nodes...')
    list_nodes = []

    # Initialize index for node_id, based on the parent node index.
    idx = parent_node_idx + 1

    # Build cross-reference lists, based on node type.
    if node_type == 'type':
        # Field type
        # Cross-references are to XSD type codes from CEDAR. Identifying these codes require special treatment.
        type_xref = build_type_xref(urlbase=urlbase)
    elif node_type == 'assay':
        dataset_xref = build_dataset_xref(urlbase=urlbase)

    for field in yaml_dict_field_nodes:
        # Get nodes associated with field.
        # The nodes object can be one of two types:
        # 1. string if the YAML has 1:1 structure--i.e.,
        #    field:node
        #    Examples: field_descriptions.yaml; field_types.yaml
        # 2. list if the YAML has 1:many structure--i.e.,
        #    field
        #    - node
        #    - node
        #    Examples: field_entities.yaml
        field_nodes = yaml_dict_field_nodes[field]
        if not isinstance(field_nodes, list):
            # 1:1 structure. Convert single element to list for matching logic.
            field_nodes = [field_nodes]

        # Add a node to the list if new to the list.
        # Fields for the node file:
        # node_id: calculated based on node's location in the list, relative to a parent node ID.
        # node_label: equivalent to preferred term
        # node_definition: definition
        # node_synonyms: will always be blank for HMFIELD nodes
        # node_dbxref: cross-reference to a code from CEDAR or HUMBMAP

        dict_node = {}

        for node in field_nodes:
            match = [n for n in list_nodes if n['node_label'] == node]
            if len(match) == 0:
                # The node is new to the list.

                # node_id
                node_id = get_node_id(idx=idx, sab=sab)

                # node_label
                if node_type == 'field':
                    #  The field name is relevant.
                    node_label = field
                else:
                    # The field name is irrelevant.
                    node_label = node

                # node_definition
                if node_type == 'field':
                    # The value from field_definitions.yaml
                    node_definition = node
                else:
                    node_definition = f'{sab} {node} {node_type}'

                # node_dbxref
                if node_type == 'field':
                    # Cross-references are to field codes from CEDAR, matched on PT.
                    xref_sab = 'CEDAR'
                    xref_term_type = 'PT'
                    xref_term_string = field
                    node_dbxref = get_codeids_for_term_sab_type(term_string=xref_term_string, sab=xref_sab,
                                                                term_type=xref_term_type, urlbase=urlbase)
                elif node_type == 'type':
                    # Use the custom cross-references for number and dateTime; otherwise, matched code from XSD.
                    if node == 'number':
                        node_dbxref = 'XSD:float'
                    elif node == 'datetime':
                        node_dbxref = 'XSD:dateTime'
                    else:
                        type_match = [x for x in type_xref if x['type'] == node]
                        if len(type_match) > 0:
                            node_dbxref = type_match[0]['code']
                        else:
                            node_dbxref = ''

                elif node_type == 'entity':
                    # HMFIELD entity cross-references are to Provenance Entity codes from HUBMAP.
                    xref_sab = 'HUBMAP'
                    xref_term_type = 'PT'

                    # Match case.
                    xref_term_string = node.capitalize()
                    node_dbxref = get_codeids_for_term_sab_type(term_string=xref_term_string, sab=xref_sab,
                                                                term_type=xref_term_type, urlbase=urlbase)

                elif node_type == 'assay':
                    # Cross-references are to Dataset Type codes in HUBMAP.
                    dataset_match = [x for x in dataset_xref if x['identifier'] == node]
                    if len(dataset_match) > 0:
                        node_dbxref = dataset_match[0]['dataset_code']
                    else:
                        node_dbxref = ''

                else:  # schema
                    # HMFIELD schemas are not cross-references
                    node_dbxref = ''

                dict_node = {'node_id': node_id, 'namespace': sab, 'node_label': node_label,
                             'node_definition': node_definition, 'node_synonyms': '', 'node_dbxrefs': node_dbxref}
                list_nodes.append(dict_node)
                idx = idx + 1

    return list_nodes


def add_nodes(path: str, list_nodes: list):
    """
    Adds rows to a nodes file.
    :param list_nodes: list of dictionaries with keys corresponding to OWLNETS nodes format.
    :param path:
    :return:
    """

    with open(path, 'a') as out:
        for field in list_nodes:
            node_id = field['node_id']
            node_namespace = field['namespace']
            node_label = field['node_label']
            node_definition = field['node_definition']
            node_synonyms = field['node_synonyms']
            # Cross-reference the HMFIELDS node to a CEDAR node.
            node_dbxrefs = field['node_dbxrefs']
            out.write(f'{node_id}\t{node_namespace}\t{node_label}\t{node_definition}'
                      f'\t{node_synonyms}\t{node_dbxrefs}\n')

    return


def initialize_file(path: str, file_type: str):
    """
    Creates and writes header for edge file.
    The edge file will be built iteratively by translating each of the relationship YAML file content.

    :param path: path to edge file
    :param file_type: edge or node
    :return:
    """

    ulog.print_and_logger_info('Building: ' + os.path.abspath(path))

    if file_type == 'edge':
        header = 'subject\tpredicate\tobject\n'
    else:
        header = 'node_id\tnode_namespace\tnode_label\tnode_definition\tnode_synonyms\tnode_dbxrefs\n'

    with open(path, 'w') as out:
        out.write(header)

    return


def add_isa(sab: str, path: str, list_nodes: list, parent_idx: int):

    """
    Builds a set of isa assertions for a list of unique, encoded nodes.
    :param sab: SAB for ingest metadata ontology
    :param path: path to edge file.
    :param list_nodes: list of unique, encoded nodes that wil be the subjects of assertions.
    :param parent_idx: index of a parent node that will be the objects of assertions.
    :return:
    """
    with open(path, 'a') as out:
        for node in list_nodes:
            subject = node['node_id']
            predicate = 'isa'
            obj = get_node_id(idx=parent_idx, sab=sab)
            out.write(f'{subject}\t{predicate}\t{obj}\n')
    return


def get_concepts_expand_request_body(concept: str, sab_list: list[str], rel_list: list[str], depth: int) -> dict:
    """
    April 2024 DEPRECATED

    Builds a request body for a call to the concepts/expand endpoint in UBKG API.
    :param concept: CUI for the concept
    :param sab_list: SABs for expansion
    :param rel_list: list of relationships
    :param depth: depth of path
    :return: dict
    """

    dict_request = {'query_concept_id': concept, 'sab': sab_list, 'rel': rel_list, 'depth': depth}

    return dict_request


def get_post_header() -> dict:
    """
    Builds a basic POST header.
    :return:
    """

    headers = {'Content-Type': 'application/json; charset=utf-8'}
    return headers


def get_concept_code(cui: str, urlbase: str, sab: str) -> str | None:
    """
    Obtains code for a CUI from the UBKG, using the concepts/{concept}/codes endpoint.
    :param cui: CUI for which to find a code.
    :param urlbase: base URL for UBKG endpoints.
    :param sab: SAB for ontology from which to select the code.
    :return: code

    """

    url = f'{urlbase}concepts/{cui}/codes'
    response = requests.get(url)
    respjson = response.json()
    # The response is a list of codes. Filter the list by the desired SAB and take the first one.
    match = [code for code in respjson if code.split(':')[0] == sab]
    if len(match) > 0:
        return match[0]
    return

def get_concept_for_code(code: str, urlbase: str) -> str | None:
    """
    Returns concept for a given code.
    :param code:
    :param urlbase: base URL for UBKG endpoints.
    :return: concept
    """
    url = f'{urlbase}codes/{code}/concepts'
    response = requests.get(url)
    respjson = response.json()
    # The response is a list of concepts. Take the first one in case of duplicates.
    if len(respjson) > 0:
        return respjson[0]['concept']
    return


def build_type_xref(urlbase: str) -> dict:
    """
    Builds a list of dictionaries of information on XSD type codes.
    :param urlbase: URL base for the UBKG API.
    :return: list of dictionaries with code information.

    Because the XSD type codes are imported as part of the CEDAR ingestion, their preferred terms have relationship
    PT_CEDAR instead of PT. This is by design.

    A consequence of the PT_CEDAR relationships is that because the valueset endpoint in hs-ontology-api assumes
    relationship type of PT, it will return no information on the codes for the children of XSD:anySimpletype.
    To obtain these codes, we use the "canonical" endpoints of the UBKG API.

    """

    # APR 2024
    # Replace deprecated POST method with new GET.

    # 1. Obtain all child concepts of XSD:anySimpletype that have CEDAR codes, using the concepts/expand endpoint.
    #url = urlbase + 'concepts/expand'
    #request_body = get_concepts_expand_request_body(concept='XSD:anySimpleType CUI', sab_list=['CEDAR'],
                                                    #rel_list=['isa'], depth=1)
    #headers = get_post_header()
    #response = requests.post(url=url, headers=headers, json=request_body)

    url = urlbase + 'concepts/XSD:anySimpleType CUI/paths/expand?sab=CEDAR&rel=isa&mindepth=1&maxdepth=2'
    response = requests.get(url)
    dict_return = response.json()

    # 2. For each child concept in the response, obtain the corresponding code from XSD.
    #for field_type in dict_return:
        #rcui = field_type.get('concept')
        #code = get_concept_code(cui=rcui, urlbase=urlbase, sab='XSD')
        #field_type['code'] = code
        # Strip the SAB from the code to get the type.
        #field_type['type'] = code.split(':')[1]

    # The paths/expand endpoint returns in a JSON in the neo4j Table frame schema. Obtain the code from
    # the nodes array.

    nodes = dict_return.get('nodes')
    for node in nodes:
        rcui = node.get('id')
        code = get_concept_code(cui=rcui, urlbase=urlbase, sab='XSD')
        node['code'] = code
        # Strip the SAB from the code to get the type.
        node['type'] = code.split(':')[1]

    return nodes


def build_dataset_xref(urlbase: str) -> list:
    """
    Builds a list of dictionaries of information on HUBMAP Dataset codes corresponding to assays
    in field_assays.yaml.
    :param urlbase: URL base for the UBKG API.
    :return: list of dictionaries with dataset information, denormalized at level of individual identifier--i.e.,
    {dataset_code:<code for node of dataset>, identifier:<data_type or an alt-name>}
    """

    # Obtain information on HUBMAP datasets using the datasets endpoint.
    url = urlbase + 'datasets?application_context=HUBMAP'
    response = requests.get(url)
    ubkg_dataset_json = response.json()

    # The datasets endpoint returns two keys of relevance:
    # 1. data_type, which corresponds to the preferred term for a property node in the Dataset Data Type hierarchy.
    # 2. alt-names, which corresponds to an optional set of synonyms (terms of type SY) for a node in the
    # Dataset Data Type hierarchy.

    # The Dataset Data Type property node has a relationship with a node in the Dataset hierarchy.
    # A HMFIELD assay will cross-reference the Dataset node instead of a node corresponding to data_type or alt_name.

    list_dataset = []
    for dataset in ubkg_dataset_json:
        dict_dataset = {}

        # Get the code for the data_type--i.e., the code for the node in the Dataset Data Type hierarchy.
        data_type_matches = get_codeids_for_term_sab_type(term_string=dataset['data_type'], sab='HUBMAP',
                                                          term_type='PT', urlbase=urlbase)
        data_type_code = data_type_matches

        # Special case: the 'Light Sheet' assay, which is an alt-name for Lightsheet that contains a space in the name.
        # The canonical UBKG API endpoint terms/{term id}/codes does not handle correctly terms with spaces.
        if dataset['data_type'] == 'Light Sheet':
            data_type_code = 'HUBMAP:C007604'

        # Obtain the CUI for the concept associated with the code. This accounts for cases in which
        # the code has been cross-referenced to another code--i.e., for which the CUI is not just the codeID + ' CUI'.
        data_type_cui = get_concept_for_code(data_type_code,urlbase=urlbase)

        # Get the code for the node in the Dataset hierarchy.
        dataset_cui = get_concept_with_relationship(cui=data_type_cui, rel='has_data_type', depth=1,
                                                    urlbase=urlbase, sab='HUBMAP')

        # The code can be obtained from the CUI.
        dataset_code = dataset_cui.split(' CUI')[0]

        # Build output.
        # Dataset:data_type
        dict_dataset = {'dataset_code': dataset_code, 'identifier': dataset['data_type']}
        list_dataset.append(dict_dataset)

        # Dataset: alt-name
        alts = dataset['alt-names']
        for alt in alts:
            dict_dataset = {'dataset_code': dataset_code, 'identifier': alt}
            list_dataset.append(dict_dataset)

    return list_dataset


def get_codeids_for_term_sab_type(term_string: str, sab: str, term_type: str, urlbase: str) -> list[str]:
    """
    Obtains a code from a SAB that corresponds to a term with a particular term type,
    using the terms/{term}/codes endpoint.
    :param term_string: term string
    :param sab: SAB for desired vocabulary
    :param term_type: term type
    :param urlbase: base URL for UBKG API
    :return: list of CodeIDs for the Code node associated with the Term node with relationship=term_type
    and name=term_string, from the specified SAB.
    """

    term_string_json = {'term': term_string}
    term_string_encoded = urllib.parse.urlencode(term_string_json).split('=')[1]

    urlcode = urlbase + 'terms/' + term_string_encoded + '/codes'

    responsecode = requests.get(urlcode)
    if responsecode.status_code != 200:
        # Call failed.
        return ''
    codejson = responsecode.json()
    if len(codejson) == 0:
        # No response
        return ''

    codematch = [code for code in codejson if (code['code'].split(':')[0] == sab and code['termtype'] == term_type)]
    if len(codematch) == 0:
        # No match
        return ''

    return codematch[0]['code']


def get_concept_with_relationship(cui: str, rel: str, depth: int, urlbase: str, sab: str) -> str:
    """
    Given a source CUI, relationship, depth, and SAB, return the CUI that has the relationship with the source CUI.
    The use case assumes 1 such concept.
    :param cui: source CUI
    :param rel: relationship
    :param depth: depth of path
    :param urlbase: base URL for the UBKG API
    :param sab: SAB for the target concept
    :return: CUI
    """

    # APRIL 2024 - Replace call to deprecated paths endpoint.
    #url = urlbase + 'concepts/paths'
    #request_body = get_concepts_expand_request_body(concept=cui, sab_list=[sab],
                                                    #rel_list=[rel], depth=depth)
    #headers = get_post_header()
    #response = requests.post(url=url, headers=headers, json=request_body)

    url = f'{urlbase}/concepts/{cui}/paths/expand?sab={sab}&rel={rel}&mindepth=1&maxdepth=2'
    response = requests.get(url)
    ubkg_response_json = response.json()

    # The paths/expand endpoint returns a JSON with the Table result frame schema.
    # The desired concept will be the source of the one element in the edges array.
    edges = ubkg_response_json.get('edges')
    match = [p for p in edges if p.get('type') == rel]
    if len(match) > 0:
        return match[0].get('source')

    return 'get_concept_with_relationship: no match'

def add_assertions(path: str, dict_associations: dict, list_fields: list, list_objects: list, predicate: str):
    """
    Adds a set of assertions to the edge file.
    :param path: Path to edge file.
    :param dict_associations: dictionary of field associations built from one of the YAML files,
    used to identify subjects and objects.
    :param list_fields: list of unique, encoded nodes for fields, used for subjects.
    :param list_objects: List of unique, encoded nodes used for objects.
    :param predicate: predicate for assertion
    :return:
    """
    ulog.print_and_logger_info(f'Asserting {predicate} relationships...')
    with open(path, 'a') as out:

        for field in dict_associations:
            # Get subject -- i.e., the node_id for the field.
            field_match = [f for f in list_fields if f['node_label'] == field]
            subj = field_match[0]['node_id']

            # Get list of associated nodes.
            # The association dictionaries are in one of two formats, based on the source YAML file.
            field_nodes = dict_associations[field]
            if not isinstance(field_nodes, list):
                # 1:1 structure. Convert single element to list for matching logic.
                field_nodes = [field_nodes]
            for node in field_nodes:
                # Find the key to match in the object list.
                objmatches = [o for o in list_objects if o['node_label'] == node]
                obj = objmatches[0]['node_id']
                out.write(f'{subj}\t{predicate}\t{obj}\n')

    return
# -----------------------------------------
# START


args = getargs()

if not args.skipbuild:
    # Read from config file.
    cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/hmfields/hmfields.ini')
    config = uconfig.ubkgConfigParser(cfgfile)

    # Get OWL and OWLNETS directories.
    # The config file contains absolute paths to the parent directories in the local repo.
    # Affix the field metadata SAB to the paths.
    owl_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owl_dir'),
                           args.sab)
    owlnets_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owlnets_dir'),
                               args.sab)
    repo_dir = config.get_value(section='Directories', key='repo_dir')

    # Get indexes for parent nodes in ontology. These will be used to define hierarchical ranges of node ids and
    # isa relationships.
    all_parent_idx = {'sab': int(config.get_value(section='Indexes', key='SAB_PARENT')),
                      'field': int(config.get_value(section='Indexes', key='FIELD_PARENT')),
                      'type': int(config.get_value(section='Indexes', key='TYPE_PARENT')),
                      'entity': int(config.get_value(section='Indexes', key='ENTITY_PARENT')),
                      'assay': int(config.get_value(section='Indexes', key='ASSAY_PARENT')),
                      'schema': int(config.get_value(section='Indexes', key='SCHEMA_PARENT'))}

    # Get the base URL to the UBKG API.
    ubkg_url = config.get_value(section='URL', key='ubkg_url')

    # Create OWLNETS related directories.
    os.makedirs(owl_dir, exist_ok=True)
    os.makedirs(owlnets_dir, exist_ok=True)

    # ------
    # Build content for node file from source YAML files in repo.
    # Build list of parent nodes.
    list_parent_nodes = build_parent_node_list(sab=args.sab, dict_index=all_parent_idx)

    # April 2024 - all file names now include "_deprecated".

    # Load field descriptions. These will be nodes in the HMFIELD ontology.
    url_field_descriptions = repo_dir + 'field-descriptions_deprecated.yaml'
    dict_fields = load_yaml(url_field_descriptions)

    # Encode and cross-references from HMFIELD fields to CEDAR fields.
    list_encoded_fields = build_node_list(sab=args.sab, yaml_dict_field_nodes=dict_fields,
                                          parent_node_idx=all_parent_idx['field'],
                                          node_type='field', urlbase=ubkg_url)

    # Field to type relationships. These will be cross-referenced to XSD field types from the CEDAR template ontology.
    url_field_types = repo_dir + 'field-types_deprecated.yaml'
    dict_field_types = load_yaml(url_field_types)
    # Unique, encoded, and cross-referenced list of HMFIELD types
    list_encoded_types = build_node_list(sab=args.sab, yaml_dict_field_nodes=dict_field_types,
                                         parent_node_idx=all_parent_idx['type'],
                                         node_type='type', urlbase=ubkg_url)

    # Field to entity relationships. These will be cross-referenced to Provenance Entity nodes in the HUBMAP ontology.
    url_field_entities = repo_dir + 'field-entities_deprecated.yaml'
    dict_field_entities = load_yaml(url_field_entities)
    # Encoded unique list of HMFIELD entities
    list_encoded_entities = build_node_list(sab=args.sab, yaml_dict_field_nodes=dict_field_entities,
                                            parent_node_idx=all_parent_idx['entity'],
                                            node_type='entity', urlbase=ubkg_url)

    # Field to assay relationships.
    # These will be cross-referenced to Dataset nodes in the HUBMAP ontology.
    url_field_assays = repo_dir + 'field-assays_deprecated.yaml'
    dict_field_assays = load_yaml(url_field_assays)
    # Unique, encoded, and cross-referenced list of HMFIELD assays
    list_encoded_assays = build_node_list(sab=args.sab, yaml_dict_field_nodes=dict_field_assays,
                                          parent_node_idx=all_parent_idx['assay'],
                                          node_type='assay', urlbase=ubkg_url)

    # Field to schema relationships.
    # These will not be cross-referenced.
    url_field_schemas = repo_dir + 'field-schemas_deprecated.yaml'
    dict_field_schemas = load_yaml(url_field_schemas)
    # Unique, encoded, and cross-referenced list of HMFIELD schemas
    list_encoded_schemas = build_node_list(sab=args.sab, yaml_dict_field_nodes=dict_field_schemas,
                                           parent_node_idx=all_parent_idx['schema'],
                                           node_type='schema',
                                           urlbase=ubkg_url)

    # Initialize the node file.
    nodes_path: str = os.path.join(owlnets_dir, 'OWLNETS_node_metadata.txt')
    ulog.print_and_logger_info(f'Writing nodes file at {nodes_path}...')
    initialize_file(path=nodes_path, file_type='node')

    # Write nodes to the node file.
    add_nodes(path=nodes_path, list_nodes=list_parent_nodes)
    add_nodes(path=nodes_path, list_nodes=list_encoded_fields)
    add_nodes(path=nodes_path, list_nodes=list_encoded_types)
    add_nodes(path=nodes_path, list_nodes=list_encoded_entities)
    add_nodes(path=nodes_path, list_nodes=list_encoded_assays)
    add_nodes(path=nodes_path, list_nodes=list_encoded_schemas)

    # ---------
    # Build the edge file.

    # Initialize the edge file.
    edgelist_path: str = os.path.join(owlnets_dir, 'OWLNETS_edgelist.txt')
    ulog.print_and_logger_info(f'Writing edge file to {edgelist_path}...')
    initialize_file(path=edgelist_path, file_type='edge')

    # Assert isa relationships.
    ulog.print_and_logger_info(f'Asserting isa relationships...')
    add_isa(path=edgelist_path, sab=args.sab, list_nodes=list_encoded_fields, parent_idx=all_parent_idx['field'])
    add_isa(path=edgelist_path, sab=args.sab, list_nodes=list_encoded_types, parent_idx=all_parent_idx['type'])
    add_isa(path=edgelist_path, sab=args.sab, list_nodes=list_encoded_entities, parent_idx=all_parent_idx['entity'])
    add_isa(path=edgelist_path, sab=args.sab, list_nodes=list_encoded_assays, parent_idx=all_parent_idx['assay'])
    add_isa(path=edgelist_path, sab=args.sab, list_nodes=list_encoded_schemas, parent_idx=all_parent_idx['schema'])

    # Translate content of the YAML files that describe relationships into assertions.
    # field: type
    add_assertions(path=edgelist_path, dict_associations=dict_field_types,
                   list_fields=list_encoded_fields, list_objects=list_encoded_types,
                   predicate='has_datatype')
    # field:entity
    add_assertions(path=edgelist_path, dict_associations=dict_field_entities,
                   list_fields=list_encoded_fields, list_objects=list_encoded_entities,
                   predicate='used_in_entity')
    # field:assay
    add_assertions(path=edgelist_path, dict_associations=dict_field_assays,
                   list_fields=list_encoded_fields, list_objects=list_encoded_assays,
                   predicate='used_in_dataset')
    # field:schema
    add_assertions(path=edgelist_path, dict_associations=dict_field_schemas,
                   list_fields=list_encoded_fields, list_objects=list_encoded_schemas,
                   predicate='used_in_schema')

    # Do not write an OWLNETS relationship file.

    exit(1)