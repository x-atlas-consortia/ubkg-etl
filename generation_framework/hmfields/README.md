# Unified Biomedical Knowledge Graph
## HMFIELD ingestion script

### Purpose
The script in this folder generates files in UBKG edges/nodes format for ingestion of content from the following YAML files:
- [field_descriptions.yaml](https://github.com/hubmapconsortium/ingest-validation-tools/blob/main/docs/field-descriptions.yaml)
- [field_types.yaml](https://github.com/hubmapconsortium/ingest-validation-tools/blob/main/docs/field-types.yaml)
- [field_entities.yaml](https://github.com/hubmapconsortium/ingest-validation-tools/blob/main/docs/field-entities.yaml)
- [field_assays.yaml](https://github.com/hubmapconsortium/ingest-validation-tools/blob/main/docs/field-assays.yaml)
- [field_schemas.yaml](https://github.com/hubmapconsortium/ingest-validation-tools/blob/main/docs/field-schemas.yaml)

These files describe ingestion metadata for datasets ingested prior to the CEDAR integration.

### Content
- **hmfields.py**: translates YAML content into a ontology graph in UBKG 
- **hmfields.ini.exmample**: Annotated example configuration file for script

### File Dependencies
1. Files in the **ubkg_utilities** folder:
   - ubkg_logging.py
   - ubkg_config.py
2. An application configuration file named **hmfields.ini.** Create this file by copying **hmfields.ini.example**.

### UBKG Dependency
Unlike other ingestions, the HMFIELD ontology queries an instance of
UBKG directly to find codes to use in assertions. The script calls endpoints
of the UBKG API. 

The **ubkg_url** field in the configuration file specifies the URL base
for UBKG endpoints.

### Translations

The script translates YAML content as follows:

#### field_descriptions.yaml
Rows in this file are translated to _field_ nodes. 
The script translates the nodes into a field hierarchy in which:
- Each field node asserts an _isa_ relationship with the **field** node.
- The **field** node asserts an _isa_ relationship with the ontology parent node.

#### field_types.yaml
This file contains mappings between fields and "data type"--e.g., string, number.
(This data type is not to be confused with the HuBMAP concept of _data_type_ used in datasets.)

The script translates the mappings from the YAML file into assertions
for which:
- **subject** is the field.
- **predicate** is _has_datatype_.
- **object** is one of the XSD data types from CEDAR.

#### field_entities.yaml
This file contains mappings between fields and HuBMAP provenance entities.

The script translates the mappings from the YAML file into assertions for which:
- **subject** is the field.
- **predicate** is _has_datatype_.
- **object** is one of the Provenance Entity codes from HUBMAP.

#### field_assays.yaml
This file contains mappings between fields and "assays" (actually dataset
types). A field can be mapped to an assay via:
- data type
- description (display name in the Portal)
- alt-name

The script translates the mappings from the YAML file into assertions for which:
- **subject** is the field.
- **predicate** is _used_for_data_type_.
- **object** is one of the HUBMAP codes for a dataset data type.

Note that although the YAML file can map a field to a dataset via data type, description, or alt-name, the script maps 
only to data type.

#### field_schemas.yaml
This file contains mappings between fields and metadata schemas.

The script builds a hierarchy out of the set of schemas in the YAML file in which:
- Each unique schema in the YAML file is translated to a _schema node_. 
- Each schema node asserts an _isa_ relationship with the **schema** node.
- The **schema** node asserts an _isa_ relationship with the ontology parent node.

The script translates the mappings from the YAML file into assertions for which:
- **subject** is the field.
- **predicate** is _used_in_schema_.
- **object** is one of the schemas from the YAML file.
