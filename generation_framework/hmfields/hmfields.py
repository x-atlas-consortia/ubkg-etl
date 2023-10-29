#!/usr/bin/env python
"""
hmfields

initial version: October 2023

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
    parser.add_argument("sab", help="SAB for ontology")
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")
    retargs = parser.parse_args()

    return retargs


def get_node_id(idx: int, sab: str) -> str:
    """
    Builds a node_id based on an index value and SAB.
    :param idx: numeric index
    :param sab: ontology SAB
    :return: str
    """
    return f'{sab}:{idx:04d}'


def build_schema_list(sab: str, yaml_dict_field_schemas: dict, parent_idx: dict) -> list:
    """
    Build a unique list of schema nodes.
    :param sab: SAB for the vocabulary.
    :param yaml_dict_field_schemas: dictionary from a YAML file--i.e., field_schemas.yaml.
    :param parent_idx: dict of indexes for parent nodes in the ontology--i.e., root, field, schema
    :return: list of encoded schemas, with each schema in a dict.
    """
    list_schemas = []

    for field in yaml_dict_field_schemas:
        # Get schemas associated with field.
        list_field_schemas = yaml_dict_field_schemas[field]
        # Add a schema to the list if new to the list.
        for schema in list_field_schemas:
            match = [s for s in list_schemas if s['schema'] == schema]
            if len(match) == 0:
                # The schema is new to the list.
                dict_schema = {'schema': schema}
                list_schemas.append(dict_schema)

    # Encode the unique list of schemas.
    idx = parent_idx['schema_parent_node_idx'] + 1
    for dict_schema in list_schemas:
        node_id = get_node_id(idx=idx, sab=sab)
        dict_schema['node_id'] = node_id
        idx = idx + 1

    return list_schemas


def write_nodes_file(sab: str, yaml_dict_fields: dict, list_schemas: list, dirpath: str, parent_idx: dict):
    """
    Writes a nodes file in OWLNETS format.
    :param sab: SAB for the ontology.
    :param yaml_dict_fields: dictionary from a YAML file. This is expected to be field_descriptions.yaml.
    :param dirpath: output directory
    :param list_schemas: list of encoded schemas built from field_schemas.YAML.
    :param parent_idx: dict of parent nodes for the ontology.
    :return:
    """

    node_metadata_path: str = os.path.join(dirpath, 'OWLNETS_node_metadata.txt')
    ulog.print_and_logger_info('Building: ' + os.path.abspath(node_metadata_path))

    with open(node_metadata_path, 'w') as out:
        out.write('node_id\tnode_namespace\tnode_label\tnode_definition\tnode_synonyms\tnode_dbxrefs\n')

        # The input dictionary is expected to be a simple list of key/value pairs:
        # key = field id
        # value = field description

        # Write parent node for ontology.
        node_id = get_node_id(idx=parent_idx['sab_parent_node_idx'], sab=sab)
        node_namespace = sab
        node_label = 'root'
        node_definition = f'{sab} ontology parent'
        node_synonyms = ''
        node_dbxrefs = ''
        out.write(f'{node_id}\t{node_namespace}\t{node_label}\t{node_definition}\t{node_synonyms}\t{node_dbxrefs}\n')

        # Write parent node for fields.
        node_id = get_node_id(idx=parent_idx['field_parent_node_idx'], sab=sab)
        node_namespace = sab
        node_label = 'field'
        node_definition = f'{sab} field'
        node_synonyms = ''
        node_dbxrefs = ''
        out.write(f'{node_id}\t{node_namespace}\t{node_label}\t{node_definition}\t{node_synonyms}\t{node_dbxrefs}\n')

        # Write parent node for schemas.
        node_id = get_node_id(idx=parent_idx['schema_parent_node_idx'], sab=sab)
        node_namespace = sab
        node_label = 'schema'
        node_definition = f'{sab} schema'
        node_synonyms = ''
        node_dbxrefs = ''
        out.write(f'{node_id}\t{node_namespace}\t{node_label}\t{node_definition}\t{node_synonyms}\t{node_dbxrefs}\n')

        # Write field nodes, which are child nodes of the field parent.
        idx = parent_idx['field_parent_node_idx'] + 1
        for key in yaml_dict_fields:
            node_id = get_node_id(idx=idx, sab=sab)
            node_namespace = sab
            node_label = key
            node_definition = yaml_dict_fields[key]
            node_synonyms = ''
            node_dbxrefs = ''

            out.write(f'{node_id}\t{node_namespace}\t{node_label}\t{node_definition}'
                      f'\t{node_synonyms}\t{node_dbxrefs}\n')

            idx = idx + 1

        # Write schema nodes. IDs for these nodes were created in the build of list_schemas.
        for schema in list_schemas:
            node_id = schema['node_id']
            node_namespace = sab
            node_label = schema['schema']
            node_definition = schema['schema'] + ' schema'
            node_synonyms = ''
            node_dbxrefs = ''
            out.write(
                f'{node_id}\t{node_namespace}\t{node_label}\t{node_definition}\t{node_synonyms}\t{node_dbxrefs}\n')

    return


def initialize_edges_file(path: str):
    """
    Creates and writes header for edge file.
    The edge file will be built iteratively by translating each of the relationship YAML file content.

    :param path: path to edge file
    :return:
    """

    ulog.print_and_logger_info('Building: ' + os.path.abspath(path))

    with open(path, 'w') as out:
        out.write('subject\tpredicate\tobject\n')

    return


def build_isa(sab: str, yaml_dict_fields: dict, list_schemas: list, path: str, parent_idx: dict):
    """
    Writes sets of isa relationships between:
        1. all nodes in dict_fields and the ontology root
        2. all schema nodes and the schema root.

    :param sab: SAB of the ontology
    :param yaml_dict_fields: dict of field nodes
    :param list_schemas: list of encoded schemas built from field_schemas.yaml.
    :param path: path to edge file
    :param parent_idx: dictionary of parent id indexes
    :return:
    """
    ulog.print_and_logger_info('Adding isa relationships to: ' + os.path.abspath(path))

    predicate = 'isa'

    with open(path, 'a') as out:

        # Relationships:
        # 1. Field parent and ontology parent.
        obj = get_node_id(parent_idx['sab_parent_node_idx'], sab=sab)
        subject = get_node_id(parent_idx['field_parent_node_idx'], sab=sab)
        out.write(f'{subject}\t{predicate}\t{obj}\n')

        # 2. Schema parent and ontology parent.
        subject = get_node_id(parent_idx['schema_parent_node_idx'], sab=sab)
        out.write(f'{subject}\t{predicate}\t{obj}\n')

        # 3. Fields and field parent.
        obj = get_node_id(parent_idx['field_parent_node_idx'], sab=sab)
        idx = parent_idx['field_parent_node_idx'] + 1
        for key in yaml_dict_fields:
            subject = get_node_id(idx=idx, sab=sab)
            predicate = 'isa'
            out.write(f'{subject}\t{predicate}\t{obj}\n')
            idx = idx + 1

        # 4. Schemas and schema parent.
        obj = get_node_id(parent_idx['schema_parent_node_idx'], sab=sab)
        for dict_schema in list_schemas:
            subject = dict_schema['node_id']
            predicate = 'isa'
            out.write(f'{subject}\t{predicate}\t{obj}\n')

    return


def ubkg_query(url: str) -> dict:
    """
    Queries the hs-ontology/UBKG API.
    :param url: URL for API endpoint
    :return:
    """
    # Call the API endpoint.
    response = requests.get(url, allow_redirects=True)

    return response.json()


def get_concepts_expand_request_body(concept: str, sab_list: list[str], rel_list: list[str], depth: int) -> dict:
    """
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


def add_field_type_relationships(yaml_dict_fields: dict, yaml_dict_field_types: dict, path: str, urlbase: str,
                                 sab: str):
    """
    Creates relationships between fields from the dict_fields YAML file and XSD field type nodes
    from CEDAR.

    Assumption: CEDAR has been ingested into UBKG.
    :param yaml_dict_fields: dictionary created from reading field_descriptions.yaml
    :param yaml_dict_field_types: dictionary created from reading field_types.yaml
    :param path: output file
    :param urlbase: URL to the UBKG API
    :param sab: ontology SAB
    :return:
    """

    ulog.print_and_logger_info('Adding field type relationships to: ' + os.path.abspath(path))

    # Because the XSD type codes are imported as part of the CEDAR ingestion, their preferred terms have relationship
    # PT_CEDAR instead of PT. This is by design.

    # A consequence of the PT_CEDAR relationships is that because the valueset endpoint in hs-ontology-api assumes
    # relationship type of PT, it will return no information on the codes for the children of XSD:anySimpletype.
    # To obtain these codes, we use the "canonical" endpdoints of the UBKG API.

    # 1. Obtain all child concepts of XSD:anySimpletype that have CEDAR codes, using the concepts/expand endpoint.
    url = urlbase + 'concepts/expand'
    request_body = get_concepts_expand_request_body(concept='XSD:anySimpleType CUI', sab_list=['CEDAR'],
                                                    rel_list=['isa'], depth=1)
    headers = get_post_header()
    response = requests.post(url=url, headers=headers, json=request_body)
    ubkg_field_type_json = response.json()

    # 2. For each child concept in the response, obtain the corresponding code from XSD.
    for field_type in ubkg_field_type_json:
        rcui = field_type.get('concept')
        code = get_concept_code(cui=rcui, urlbase=urlbase, sab='XSD')
        field_type['code'] = code
        # Strip the SAB from the code to get the type.
        field_type['type'] = code.split(':')[1]

    # 3. Loop through the YAML dictionary of fields.
    # Match the field's type to an XSD type from the UBKG.
    # Write a "has_datatype" relationship to the edge file. The "has_datatype" relationship matches that used in CEDAR.

    with open(path, 'a') as out:
        idx = 1
        for key in yaml_dict_fields:
            subj = get_node_id(idx=idx, sab=sab)
            yaml_field_type = yaml_dict_field_types.get(key)
            # The YAML file currently has lower type resolution for numbers than available in XSD. The YAML uses
            # "number". XSD has types for integer, float, and decimal, but not number. Map "number" to XSD:float
            # for now.
            obj = ''
            if yaml_field_type == 'number':
                obj = 'XSD:float'
            # The YAML file has a type of "datetime". The corresponding XSD type is dateTime.
            elif yaml_field_type == 'datetime':
                obj = 'XSD:dateTime'
            else:
                # The general use case. Look for a 1:1 match between YAML type and XSD type.
                match = [field_type for field_type in ubkg_field_type_json if field_type['type'] == yaml_field_type]
                if len(match) > 0:
                    obj = match[0].get('code')
            if obj != '':
                predicate = 'has_datatype'
                out.write(f'{subj}\t{predicate}\t{obj}\n')

            idx = idx + 1

    return


def add_field_entity_relationships(yaml_dict_fields: dict, yaml_dict_field_entities: dict, path: str,
                                   urlbase: str, sab: str):
    """
        Creates relationships between fields from the dict_fields YAML file and codes in the Provenance Entity
        hierarchy of the HUBMAP ontology.

        Assumption: CEDAR has been ingested into UBKG.
        :param yaml_dict_fields: dictionary created from reading field_descriptions.yaml
        :param yaml_dict_field_entities: dictionary created from reading field_entities.yaml
        :param path: output file
        :param urlbase: URL to the UBKG API
        :param sab: ontology SAB
        :return:
        """

    ulog.print_and_logger_info('Adding field entity relationships to: ' + os.path.abspath(path))

    # Obtain information on HUBMAP codes and terms for children of HUBMAP:C040000 (Provenance Entity),
    # using the valueset endpoint.
    url = urlbase + 'valueset?application_context=HUBMAP&parent_sab=HUBMAP&parent_code=C040000&child_sabs=HUBMAP'
    response = requests.get(url)
    ubkg_entity_json = response.json()

    # Loop through the YAML dictionary of fields.
    # Match the field's associated entities from the field-entity YAML to entities from the UBKG.
    # Write a "used_in_entity" relationship to the edge file.

    with open(path, 'a') as out:
        idx = 1
        for key in yaml_dict_fields:
            subj = get_node_id(idx=idx, sab=sab)

            # A field maps to a list of entities.
            yaml_field_entities = yaml_dict_field_entities.get(key)
            for entity in yaml_field_entities:
                # Terms for Provenance Entity codes from UBKG are in mixed case; entities in the YAML are in lowercase.
                matches = [ubkg_entity for ubkg_entity in ubkg_entity_json if
                           ubkg_entity['term'].lower() == entity]
                for m in matches:
                    # Build the CodeID from the SAB and CODE.
                    obj = m.get('sab') + ':' + m.get('code')
                    predicate = 'used_in_entity'
                    out.write(f'{subj}\t{predicate}\t{obj}\n')

            idx = idx + 1

    return


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
    codejson = responsecode.json()
    codematches = [code for code in codejson if (code['code'].split(':')[0] == sab and code['termtype'] == term_type)]
    return codematches


def add_field_assay_relationships(yaml_dict_fields: dict, yaml_dict_field_assays: dict, path: str, urlbase: str,
                                  sab: str):
    """
        Creates relationships between fields from the dict_fields YAML file and codes in the Dataset Data Type
        hierarchy of the HUBMAP ontology.

        :param yaml_dict_fields: dictionary created from reading field_descriptions.yaml
        :param yaml_dict_field_assays: dictionary created from reading field_assays.yaml
        :param path: output file
        :param urlbase: URL to the UBKG API
        :param sab: ontology SAB
        :return:
        """

    ulog.print_and_logger_info('Adding field assay relationships to: ' + os.path.abspath(path))

    # Obtain information on HUBMAP datasets using the datasets endpoint.
    url = urlbase + 'datasets?application_context=HUBMAP'
    response = requests.get(url)
    ubkg_dataset_json = response.json()

    # The datasets endpoint returns three keys of relevance:
    # 1. data_type, which corresponds to the preferred term for a node in the Dataset Data Type hierarchy.
    # 2. description, which corresponds to the preferred term for a node in the Dataset Display name hierarchy.
    # 3. alt-names, which corresponds to synonyms (terms of type SY) for a node in the Dataset Data Type hierarchy.

    # The field_assays.yaml file can use any of these to describe an assay.

    # We need the corresponding code in the Code node in the HUBMAP ontology corresponding to the data type.
    # Use the terms/{term}/codes endpoint and filter on codes with SAB of HUBMAP for which the data_type is the PT.
    # Athough the return from get_codeids_for_term_sab_type is a list, it should only contain one code in this case.
    for dataset in ubkg_dataset_json:
        codematches = get_codeids_for_term_sab_type(term_string=dataset['data_type'], sab='HUBMAP',
                                                    term_type='PT', urlbase=urlbase)
        dataset['code'] = codematches[0]['code']

    # Loop through the YAML dictionary of fields.
    # Match the field's associated assay from the field-assay YAML to entities from the UBKG,
    # searching on data_type, description, or alt-names.
    # Write a "used_for_data_type" relationship to the edge file.

    with open(path, 'a') as out:
        idx = 1

        for key in yaml_dict_fields:

            matches = []  # initialize
            subj = get_node_id(idx=idx, sab=sab)

            # A field maps to a list of "assays", using a combination of data_types, display names, and alt-names.
            yaml_field_assays = yaml_dict_field_assays.get(key)

            if yaml_field_assays is not None:
                # Try to match for each assay associated with the field in field_assays.yaml.
                for assay in yaml_field_assays:

                    # Match against data_type.
                    matches_data_type = [ubkg_dataset for ubkg_dataset in ubkg_dataset_json if
                                         ubkg_dataset['data_type'] == assay]

                    # Match against description (display name).
                    matches_description = [ubkg_dataset for ubkg_dataset in ubkg_dataset_json if
                                           ubkg_dataset['description'] == assay]

                    # Match against alt-names.
                    matches_alt_names = [ubkg_dataset for ubkg_dataset in ubkg_dataset_json if
                                         assay in ubkg_dataset['alt-names']]

                    if len(matches_data_type) > 0:
                        matches.extend(matches_data_type)
                    elif len(matches_description) > 0:
                        matches.extend(matches_description)
                    elif len(matches_alt_names) > 0:
                        matches.extend(matches_alt_names)
                    else:
                        ulog.print_and_logger_info(
                            f'Field {key} - assay {assay} not matched to an assay in UBKG.')

                    if len(matches) > 0:
                        # Write the assertions.
                        for match in matches:
                            obj = match.get('code')
                            predicate = 'used_for_data_type'
                            out.write(f'{subj}\t{predicate}\t{obj}\n')

            else:
                ulog.print_and_logger_info(f'Field {key} not associated with an assay in field_assays.yaml.')

            idx = idx + 1

        return


def add_field_schema_relationships(yaml_dict_fields: dict, yaml_dict_field_schemas: dict, list_schemas: list,
                                   path: str, sab: str):
    """
    Creates relationships between fields from the dict_field_descriptions YAML file and schemas from the
    field_schemas YAML file.
    :param yaml_dict_fields: dictionary built from field_descriptions.yaml
    :param yaml_dict_field_schemas: dictionary built from field_schemas.yaml
    :param list_schemas: list of encoded schemas built from field_schemas.yaml.
    :param path: output path
    :param sab: SAB
    :return:
    """

    with open(path, 'a') as out:

        idx = 1
        for field in yaml_dict_fields:
            subj = get_node_id(idx=idx, sab=sab)

            # Get the schemas associated with the field.
            field_schemas = yaml_dict_field_schemas.get(field)

            if field_schemas is not None:
                # Get the node_id for each schema. Write an edge between the field and the schema.
                for schema in field_schemas:
                    encoded_schema = [s for s in list_schemas if s['schema'] == schema]
                    obj = encoded_schema[0]['node_id']
                    predicate = 'used_in_schema'
                    out.write(f'{subj}\t{predicate}\t{obj}\n')

            idx = idx + 1


# -----------------------------------------
# START

args = getargs()

# Read from config file.
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/hmfields/hmfields.ini')
config = uconfig.ubkgConfigParser(cfgfile)

# Get OWL and OWLNETS directories.
# The config file contains absolute paths to the parent directories in the local repo.
# Affix the SAB to the paths.
owl_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owl_dir'),
                       args.sab)
owlnets_dir = os.path.join(os.path.dirname(os.getcwd()), config.get_value(section='Directories', key='owlnets_dir'),
                           args.sab)
repo_dir = config.get_value(section='Directories', key='repo_dir')

# Get indexes for parent nodes in ontology. These will be used to define hierarchical ranges of node ids and
# isa relationships.
sab_parent_idx = {'sab_parent_node_idx': int(config.get_value(section='Indexes', key='SAB_PARENT')),
                  'field_parent_node_idx': int(config.get_value(section='Indexes', key='FIELD_PARENT')),
                  'schema_parent_node_idx': int(config.get_value(section='Indexes', key='SCHEMA_PARENT'))}

# Get the base URL to the UBKG API.
ubkg_url = config.get_value(section='URL', key='ubkg_url')

if not args.skipbuild:
    # Create OWLNETS related directories.
    os.makedirs(owl_dir, exist_ok=True)
    os.makedirs(owlnets_dir, exist_ok=True)

    # Build edge and node files from source files in repo.

    # Get field descriptions. These will be nodes in the HMFIELD ontology.
    url_field_descriptions = repo_dir + 'field-descriptions.yaml'
    dict_fields = load_yaml(url_field_descriptions)

    # Field to field type relationships. These will use existing XSD field types from the CEDAR template ontology.
    url_field_types = repo_dir + 'field-types.yaml'
    dict_field_types = load_yaml(url_field_types)

    # Field to entity relationships. These will be mapped to entities nodes in the HUBMAP ontology.
    url_field_entities = repo_dir + 'field-entities.yaml'
    dict_field_entities = load_yaml(url_field_entities)

    # Field to assay (dataset data type) relationships.
    # These will be mapped to dataset data types in the HUBMAP ontology.
    url_field_assays = repo_dir + 'field-assays.yaml'
    dict_field_assays = load_yaml(url_field_assays)

    # Field to schema relationships.
    url_field_schemas = repo_dir + 'field-schemas.yaml'
    dict_field_schemas = load_yaml(url_field_schemas)
    list_encoded_schemas = build_schema_list(sab=args.sab, yaml_dict_field_schemas=dict_field_schemas,
                                             parent_idx=sab_parent_idx)

    # Write the node file.
    write_nodes_file(sab=args.sab, yaml_dict_fields=dict_fields, list_schemas=list_encoded_schemas,
                     dirpath=owlnets_dir, parent_idx=sab_parent_idx)

    # Initialize the edge file.
    edgelist_path: str = os.path.join(owlnets_dir, 'OWLNETS_edgelist.txt')
    initialize_edges_file(path=edgelist_path)

    # Assert isa relationships.
    build_isa(sab=args.sab, yaml_dict_fields=dict_fields, list_schemas=list_encoded_schemas, path=edgelist_path,
              parent_idx=sab_parent_idx)

    # Translate content of the YAML files that describe relationships into assertions.

    # Field type
    add_field_type_relationships(yaml_dict_fields=dict_fields, yaml_dict_field_types=dict_field_types,
                                 path=edgelist_path, urlbase=ubkg_url, sab=args.sab)

    # Provenance entity
    add_field_entity_relationships(yaml_dict_fields=dict_fields, yaml_dict_field_entities=dict_field_entities,
                                   path=edgelist_path, urlbase=ubkg_url, sab=args.sab)

    # Assay (dataset data type)
    add_field_assay_relationships(yaml_dict_fields=dict_fields, yaml_dict_field_assays=dict_field_assays,
                                  path=edgelist_path, urlbase=ubkg_url, sab=args.sab)

    # Schema
    add_field_schema_relationships(yaml_dict_fields=dict_fields, yaml_dict_field_schemas=dict_field_schemas,
                                   list_schemas=list_encoded_schemas,
                                   path=edgelist_path, sab=args.sab)

