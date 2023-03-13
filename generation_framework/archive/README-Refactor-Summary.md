# Knowledge Base ETL Workflow Refactoring

## Introduction
This document explains how the current ETL Process for loading the Knowledge Base should be refactored.  The process will start with the UMLS .CSV files loaded using these steps: https://github.com/dbmi-pitt/UMLS-Graph/blob/master/CSV-Extracts.md.  These files form the UMLS basis for the rest of the process.  This code is currently in `refactored_code` branch in github.

## Prerequisites
There are 5 file structures used by the refactored code.  These files follow a format initially developed by the PheKnowLator project.  **PLEASE NOTE: These files cannot contain any extra information.  The load process assumes there is no further filtering required to process this data.  Some errors may occur if extra entities or relations are found within the data.** The files and formats are presented below:  
* **node metadata**- This file contains a list of the "main entities" within the data.  These will include: genes, anatomic locations, proteins, diseases, etc.  There should only be one entry for each entity in this file.  This file includes the follwing columns:
  * **ontology_uri**- this column contains a unique identifier for the entity (typically an ontology URI).  This identifier is found in other files like the dbxref and edge list file.
  * **codeid**- this column contains an SAB prefix plus a code for the **ontology_uri** (ex: FMA 12345, MSH OU812).  This column will be parsed to set the **code** properties in the neo4j graph.  **IMPORTANT: For *ontology_uris* matching existing codes, this column must match the existing code (ex: FMA 12345, MSH OU812).**
  * **node_label**- the 'preferred term' for the entity.  
  * **node_definition**- a definition for the entity.
* **dbxref**- This file contains a list of cross-references for each **ontology_uri**.  The cross-references are a pipe-delimited list.  The individual cross-references adhere to a `<prefix> <identifier>` format.   
  * **ontology_uri**- the same unique identifier as found int the **node metadata** file.
  * **dbxrefs**- a pipe-delimited list of cross references (ex: `FMA 67860|BTO 0004185`).  **IMPORTANT: this column must match the existing codes.**
* **edge list**- This file contains relations between two **ontology_uri** identifiers.  A single **ontology_uri** can be found multiple times in this file.  The file format follows the N-triples from RDF: `subject   predicate   object .` where each line expresses a single statement.  Each statement can be read like a short English sentence.  For example, `UBERON_xyz has_part    UBERON_abc` reads "UBERON_xyz has a part UBERON_abc".
  * **subject**- The first identifier of the statement. It is the thing "owning" the predicate.  The same unique identifier as found int the **node metadata** file.
  * **predicate**- The relationship between the subject and object (ex: has_part, regulates, etc.).  The predicate is a URI found in the **relations** file.
  * **object**- The second identifier in the statement.  It is the target of the predicate.  
* **synonym list**- This file contains a list of **ontology_uri** and a list of strings representing the **ontology_uri's** synonyms.  In this file, the **ontology_uri** will repeat on several lines if there are multiple synonyms.  **PLEASE NOTE: Do not include any preferred terms in this file.  Only include synonyms.**    
  * **ontology_uri** the same unique identifier as found int the **node metadata** file.
  * **codeid**- this column contains an SAB prefix plus a code for the **ontology_uri** (ex: UBERON 12345, CL OU812).  
  * **synonym** the synonym for the **ontology_uri**
* **relations** This file has a single entry for each unique **predicate** found in the **edge_list** file.  It also provides an English label for each relation.
  * **relation_id** The URI for the relation.  The relation URI should only be found in the list once.
  * **relation_label** The English label for the relation.
  * **inverse_relation_label** The English label for the inverse of the relation.  An inverse_relation_label does not need a corresponding relation_id.

### File Requirements
The code does not enforce these requirements, but there are some implied relationships between these files.  At some point the code should be modified to check these requirements.  
1.  There is a one-to-one relation between the node_metadata, dbxref, and edge_list.  You need a set of these files for each SAB (aka ontology) you want to load.  For example, if you want to load UBERON you will need a set of UBERON node_metadata, dbxref, and edge_list files.
2.  The synonym file is optional for any SAB.
3.  The relations file can be a single file representing a superset of all the relations across all SABs.  Alternatively, it can be a set of files. 
## Configuration File
The configuration file will direct the data load process.  The refactor modifies one existing setting  and adds 5 items to the configuration file.  The new configuration file expects all the ontology files to live in the same directory `ONTOLOGY_SOURCE_DIR`.  Prior versions of the configuration file had several separate locations for the ontology files.  The file adds 5 settings:
* EDGE_LIST_FILE_TABLE_INFO
* NODE_METADATA_FILE_TABLE_INFO
* DBXREF_FILE_TABLE_INFO
* SYNONYM_LIST_FILE_TABLE_INFO
* RELATIONS_FILE_TABLE_INFO  

Each of these settings contains an array with objects.  **The order of the objects is important.  The objects must be listed in the correct order for "layering" the data.  If ontology A depends on ontology B then ontology B must be listed first.**  Each object contains this information:
* **file_name**- The name of the file to load.
* **table_name**- The name of the table to create from the data in the file.
* **SAB**- The SAB to be used when loading this data.

An example of these 5 settings is below:
```python
EDGE_LIST_FILE_TABLE_INFO = [{'table_name':'uberon_edge_list','file_name':'uberon_edge.txt','SAB':'UBERON'},
{'table_name':'cl_edge_list','file_name':'cl_edge.txt','SAB':'CL'}]
NODE_METADATA_FILE_TABLE_INFO = [{'table_name':'uberon_node_metadata','file_name':'uberon_node_metadata.txt','SAB':'UBERON'},
{'table_name':'cl_node_metadata','file_name':'cl_node_metadata.txt','SAB':'CL'}]
DBXREF_FILE_TABLE_INFO = [{'table_name':'uberon_dbxref','file_name':'uberon_dbxref.txt','SAB':'UBERON'},
{'table_name':'cl_dbxref','file_name':'cl_dbxref.txt','SAB':'CL'}]
SYNONYM_FILE_TABLE_INFO = [{'table_name':'uberon_synonym_list','file_name':'uberon_synonym.txt','SAB':'UBERON'},
{'table_name':'cl_dbxref','file_name':'cl_dbxref.txt','SAB':'CL'}]
RELATIONS_FILE_TABLE_INFO = [{'table_name':'uberon_relations','file_name':'uberon_relations.txt','SAB':'UBERON'},
{'table_name':'cl_relations','file_name':'cl_relations.txt','SAB':'CL'}]
```  

## Code Workflow
### Extract Step
The `extract(config)` method in `load_csv_data.py` changes a bit.  The `load_umls_xxx(config)` methods remain in place.  Five new methods are added to `extract(config)`: `load_edge_list`, `load_node_metadata`, `load_dbxref`, `load_synonym_list`, and `load_relations`.  These five methods do the same thing:
1.  Create a for loop using one of the configuration items (EDGE_LIST_FILE_TABLE_INFO, NODE_METADATA_FILE_TABLE_INFO, etc.)
2.  Use the table_name and file_name from each object as parameters for the `load_file(config, file_path, table_name)` method

The `load_file(config, file_path, table_name)` needs to be updated to create the table for the table_name parameter.  The table creation will vary depending on the type of file being loaded (ex: edge_list, node_metadata, etc.)  

The `create_indices(config)` method needs to change.  It should use the 5 new configuration items (EDGE_LIST_FILE_TABLE_INFO, NODE_METADATA_FILE_TABLE_INFO, etc.) as parameters.  It will use these table_names to create indices for the tables created from the configuration files.  


The new `extract(config)` method looks like this:
```python
    create_database(config)
    load_node_metadata(config)
    load_relations(config)
    load_dbxref(config)
    load_edge_list(config)
    load_synonym_list(config)
    load_umls_codes(config)
    load_umls_defs(config)
    load_umls_suis(config)
    load_umls_cuis(config)
    load_umls_tuis(config)
    load_umls_cui_codes(config)
    load_umls_code_suis(config)
    load_umls_cui_cuis(config)
    load_umls_cui_suis(config)
    load_umls_cui_tuis(config)
    load_umls_def_rel(config)
    load_umls_tui_rel(config)
    create_indices(config)
    print("Done with extract process")
```
The `load_node_metadata(config)`,    `load_relations(config)`,`load_dbxref(config)`, `load_edge_list(config)`,`load_synonym_list(config)` methods all follow the same general pattern:
1.  Access one of the `FILE_TABLE_INFO` config variables like `EDGE_LIST_FILE_TABLE_INFO`, `NODE_METADATA_FILE_TABLE_INFO`, etc.
2.  For each entry, extract the `table_name`, `file_name`, and `sab` from the `FILE_TABLE_INFO` config variable
3. Use `CREATE TABLE` SQL statement to create a table called `table_name`
4. Use the `load_file` method to load the `file_name` data into the newly created `table_name` SQL table
5. Update the records in the newly created `table_name` SQL table to fill in the `sab` column
### Transform Step
The `transform(config)` method changes quite a bit in the refactored code.  First, `build_xref_table(config)` is added to the start of the `transform(config)` method.  The changes look like this:  
```python
    build_xref_table(config)
    build_ambiguous_codes_table(config)
    build_ontology_uri_to_umls_map_table(config)
    build_relations_table(config)
    insert_new_cuis(config)
    insert_new_codes(config)
    insert_new_terms(config)
    insert_new_defs(config)
    insert_new_cui_cui_relations(config)
```
Most of the methods in the 'transform(config)` method follow a general pattern of steps:
1.  Access one of the `FILE_TABLE_INFO` config variables like `EDGE_LIST_FILE_TABLE_INFO`, `NODE_METADATA_FILE_TABLE_INFO`, etc.
2.  Use the `FILE_TABLE_INFO` variable to walk through the existing mysql tables (created in the `extract(config)` method).  
3.  For each `table_name` in the `FILE_TABLE_INFO` variable, include the mysql table in a SQL query to build the parts of the graph (CUIs, SUIs, Codes, etc.)
### Load Step
The `load(config)` method does not change in the refactored code.

## Running the Code
### Step 1: Building neo4j Graph CSV Files
The `ontology-api/src/neo4j_loader/load_csv_data.py` file creates all the CSV files necessary to load neo4j.  The code relies upon a file called `app.cfg`.  This file is based off the `app.cfg.example` file.  Once the `app.cfg` file is in place, you can run the `load_csv_data.py` code.  The `load_csv_data.py` code takes three parameters:
* extract- run the `extract(config)` method.  This reads all the CSV files and creates the starting SQL tables.  This method takes the longest amount of time to run.
* transform- run the `transform(config)` method.  This method reads the data written in the `extract(config)` step.  The method is written so it can be run repeatedly.  In other words, all the new data added in previous runs of this steps is removed from the database while this code runs (either through `DROP TABLE` or SQL `DELETE` statements).  This step takes the least amount of time to run.
* load- run the `load(config)` method.  This method takes the data from the `transform(config)` step and writes it out to a set of CSV files

These parameters can be used singly or in sequence.  For instance:  
`python3 load_csv_data.py extract`  
`python3 load_csv_data.py extract transform`  
`python3 load_csv_data.py extract transform load` (runs the whole workflow)  
`python3 load_csv_data.py transform load` (can be run after the extract step has run)  
### Step 2: Loading the neo4j Graph
The `ontology-api/src/neo4j_loader/reload_neo4j_data.sh` bash script runs a series of commands that does the following:
1.  Stops neo4j
2.  Deletes the existing neo4j data in preparation for the `neo4j-admin import` step.
3.  Copies the CSV files created by the `load_csv_data.py` into the neo4j `import` directories.
4.  Executes the `neo4j-admin import` step (it has to be done against a stopped neo4j instance).
5.  Set the initial password for the `neo4j` user in the neo4j graph (the password is a parameter of the `reload_neo4j_data.sh` script)
6.  Start neo4j
7.  Run a series of neo4j cypher commands (and .cql files) to remove some orphaned data and create indices.

To use the `reload_neo4j_data.sh` you must be sudo:  
`sudo ./reload_neo4j_data.sh 1234` (where 1234 is the new password)

## Loose Ends
* The `reload_neo4j_data.sh` script works, but it contains several hard-coded paths.  I think it could import a lot of its information from app.cfg.
* The NDC .CSV files are disjoint from the rest of the UMLS data processing.  This is acceptable from a coding perspective (in other words the code doesn't need the NDC data), but it requires the `reload_neo4j_data.sh` script to copy them into place separately.
* The `load_csv_data.py` code does not do much error checking.  For example, it does not check if the number of node_metadata files matches the edge_list files.  It also does not check if all the ontology_uris exist in various files.
* The `app.cfg` file contains entries for the neo4j connection.  These entries might be useful if the `reload_neo4j_data.sh` script is modified to read data from `app.cfg`.
* It might be useful to add nodes to track the version information for the vocabularies/ontologies loaded into the Knoweldge Graph.  It may also be useful to add an overall version node to track when the whole Knowledge Graph was built.
* It might be useful to add the ontology URI to all the Code nodes.  The current approach requires the user to determine which vocabulary/ontology is dependent on other vocabulary/ontology.  The vocabularies/ontologies lack any globally unique identifiers.  If the data is loaded in the wrong order, it will create duplicate Concept nodes (CUIs).  If we included the ontology URI then we could relax the dependency requirement.  We would not create duplicate CUIs becuase the ontology URI would provide a unique identifier.  We could use the URI to determine if the node already exists or if we are looking at a new node.
* The code assumes that each source file (cl_node_metadata.txt, uberon_relations.txt, etc.) contains data from one SAB (UBERON, CL, etc.).  The code could be modified to allow one file to contain multiple SABs but it would require the source files to add an SAB column.
* There is an `ontology-api/test/test_load_csv_data.py` test code.  This code uses the neo4j connection entries in the `app.cfg` file.  I think the tests are still valid, but they will definitely need to change over time.  The `setUp(self)` method contains a hardcoded path to find `app.cfg`.  This path should be made relative.




