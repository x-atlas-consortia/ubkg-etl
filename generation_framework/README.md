# Unified Biomedical Knowledge Graph Generation Framework

## Background
The application architecture that supports the UBKG includes a knowledge graph representing a polyhierarchical organization of 
interconnected ontologies. 

The scripts in this folder path are used to convert data from ontologies into 
formats that can be appended to the set of UMLS CSV files.

![generation_framework](https://user-images.githubusercontent.com/10928372/202733307-d9a7c76d-8a0a-401f-a0e2-011d8449ac41.jpg)

# Basic workflow
The integration of an ontology into the UBKG requires two types of script file:

### 1. OWLNETS: triple store information--edges, nodes, and (optional) relations metadata

Source data from an ontology is converted into files of triple store data--i.e.,
* _edges_, or triples of assertions in subject | predicate | object format
* _nodes_ metadata
* optional _relations_ metadata

* For ontologies that are published in OWL files, the triple store data is in a set of files in [OWLNETS](https://github.com/callahantiff/PheKnowLator/wiki/OWL-NETS-2.0) format. The OWL files are converted using the PheKnowLator package, as
* For ontologies that are not described in OWL files (e.g., HUBMAP, UNIPROTKB), custom converters create files that conform to the OWLNETS format.

### 2. Integration of assertions into CSV files 
The OWLNETS-UMLS-GRAPH script, described below, converts data from the triple store files into content that can be integrated into the base UMLS CSV structure.

### Logging

Information is logged to a file './builds/logs/pkt_build_log.log'.

### Integration of an ontology

Integrating an ontology into UBKG involves the following steps:
1. Build the necessary conversion script:
- For ontologies from OWL files, the script based in PheKnowLator should be sufficient.
- For other data, a custom script will be required.
2. Add an entry to the ontologies.json file.
3. Call the script with an argument that corresponds to the SAB (identifier for the ontology)
 
Parameters in the build_csv.**py** script (called by the build_csv.**sh** shell script) control processing.

### ontology.json

The file [ontologies.json](https://github.com/dbmi-pitt/UBKG/blob/main/Generation_framework/ontologies.json) is used to direct conversion of an ontology or data source.

- For ontologies that are describe in published OWL files, the relevant key/value pairs are:
* "owl_url": the URL to download the OWL file
* "home_url": the URL that describes the OWL

- For ontologies or data sources with custom converters, the "execute" key/value specifies the location of the conversion script.


```
"MONDO": {
    "owl_url": "http://purl.obolibrary.org/obo/mondo.owl",
    "home_url": "https://obofoundry.org/ontology/mondo.html",
    "comment": "The Mondo Disease Ontology (MONDO): a global community effort to harmonize multiple disease resources to yield a coherent merged ontology"
  },
  "HUBMAP": {
    "comment": "HubMAP application ontology, obtained from input spreadsheet in SimpleKnowledge format",
    "execute": "./skowlnets/skowlnets.py SimpleKnowledgeHuBMAP.xlsx HUBMAP"
  }
```

The JSON file allows for both the conversion of OWL-based files and custom conversion.

### Regenerating without downloading or OWLNETS conversion
Once the script has been run on the local machine for an ontology, it is possible 
to rerun the script without generating triple store data by downloading source files (e.g, OWL files) or running the OWL-OWLNETS conversion scripts again. 

This avoids the need to obtain source data for ontologies that do not update often.

To run the script without regenerating triple store data, use the -s parameter.

Example of running the script with SAB arguments:
```
$ cd scripts
$ ./build_csv.sh -v PATO UBERON CL DOID CCFASCTB OBI EDAM HSAPDV SBO MI CHEBI MP ORDO PR UO HUSAT HUBMAP UNIPROTKB
```
The UBKG CSV files can be enhanced iteratively by calling the script successively, as illustrated in the architecture diagram.
For example, two calls to the script

```
./build_csv.sh -v PATO
./build_csv.sh -v UBERON
```
are equivalent to the call that combines the arguments
```
./build_csv.sh -v PATO UBERON
```

## References between ontologies and order of generation

Nodes in an ontologies can refer to nodes in other ontologies in two ways:
1. Via **relationships**--e.g., a node for a protein in UNIPROTKB has a _gene product of_ relationship with a gene node in HGNC.
2. Via **equivalence classes** (cross-references)--e.g., a node in HUBMAP may be equivalent to a node in OBI.

If an ontology refers to nodes in another ontology, the referred ontology nodes should be defined 
one of two places:

1. The OWLNETS_node_metadata.txt file of the ontology. (For example, the PATO ontology refers to nodes in ontologies like CHEBI, but defines them with distinct IRIs in the node metadata.)
2. The ontology CSV files--in particular, CUI-CODES.CSV.

In other words, relationships between ontologies determines the order in which they are integrated.

The content of a particular implementation of a UBKG database depends on the set of assertiions integrated. Different implementations may integrate different sets of assertions: for example, project one may include assertions from the set {PATO,UBERON,CL,DOID,EDAM}, while another may include {PATO,UBERON,CL,DOID,CHEBI,ORDO}.

The file [README-PARAMETER ORDER for generation.md](https://github.com/dbmi-pitt/ubkg/blob/main/scripts/README-PARAMETER%20ORDER%20for%20generation.md) provides the most current recommendations for generating different
instances of the UBKG.

### Sample triplet conversion times by ontology

The build script is run on a local development machine. The bulk of the processing involves the PheKnowLator conversion of OWL files to OWLNETS triple store files.

Sample OWLNETS conversion times per ontology when run on a MacBook Pro 32 GB M1 running Ventura:

* PATO: 1 minute
* UBERON: 4 minutes
* CL: 3 minutes
* DOID: 2 minutes
* CCFASCTB: 1 minute
* OBI: 1 minute
* EDAM: 1 minute
* HSAPDV: 1 minute
* SBO: 1 minute
* MI: 1 minute
* **CHEBI: 8 hours**
* MP: 8 minutes
* ORDO: 6 minutes
* **PR: 11 hours**
* HUSAT: 1 minute
* HUBMAP: 1 minute
* UNIPROTKB: 5 minutes


## OWL to OWLNETS files

The './owlnets_script/__main__.py' is used to convert OWL files to OWLNETS format (tab delimited files).
Running this file with a '-h' parameter will give a list of arguments and optional arguments.
This file is essentially the [PheKnowLator OWLNETS Example Application](https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb) with some additional housekeeping.
It will download a file to './pkt_kg/libs/owltools' automatically.

It will process as follows:

### OWL Input

The .OWL file is read from the web and stored in the './owl/***ontology***' directory (with the '.owl' extension).
After that the MD5 of that file is computed and stored in a file with a .md5 extension in the same directory.
The MD5 is compared on subsequent processing, and also serves as a part of the build manifest.
If the computed MD5 does not match the MD5 found in the .md5 file, an error is generated; in general this should not happen.

### OWLNETS Output

The OWLNETS files are written to the '/owlnets_output/***ontology***' directory.
Subsequent processing is concerned with the three files of the form 'OWLNETS_*.txt'.
These are tab delimited text files that are read by the 'OWLNETS-UMLS-GRAPH.py' program.

## OWLNETS files to CSV files

The OWLNETS files are converted to .CSV (comma delimited) files by the script located in './Jonathan/OWLNETS-UMLS-GRAPH.py'.
This script takes its input from the './owlnets_output/' files, and a base set of [UMLS](https://www.nlm.nih.gov/research/umls/index.html) (.csv files) files.
It writes to the '../neo4j/import/current' directory.
Its changes to the files in that directory are cumulative between runs, so when starting a run a freshly downloaded set of UMLS files should be placed there.
The script that coordinates the running of this process will copy the current .csv files to a numbered save directory (e.g., 'save.1') so that the results of intermediate iterations can be examined.
In the end, it is only the final set of .csv files that is used as a basis for the neo4j graph.

## Coordination

The process is coordinated via the 'build_csv.sh' file which (after setting up a python environment) will run the build_csh.py file where the logic is located.
The python virtual environment is placed in the './venv' directory using the './requirements.txt' file.

A prerequisite for running this file is that python3 be installed. It is also configured to run in OSX (MacBook Pro) currently.

### Processing

The 'build_csv.py' file takes an optional parameter '-h' which allows you to see other parameters.


The script runs a loop over the Owl URI list specified in the 'OWL_URLS' variable, processing each Owl file as follows:
1. Run the 'owlnets_script/__main__.py' program over the OWL file after downloading it to the 'owl/&lt;OWL&gt;/' directory, and generating the .md5 file associated with it in that directory.
2. Copy the .csv files found in '../neo4j/import/current' to a save directory at the same level (e.g., 'save.3/).
3. Run the 'Jonathan/OWLNETS-UMLS-GRAPH.py' over the owlnets_script generated files in the 'owlnets_output/&lt;OWL&gt;/' directory. This will modify the .csv files found in the '../neo4j/import/current' with the output from step 1. for the Owl file processed there.

This process repeats until all of the OWL files are processed.
The resulting .csv files can then be used to create a new Neo4j database (see the README.md file in the neo4j directory).
