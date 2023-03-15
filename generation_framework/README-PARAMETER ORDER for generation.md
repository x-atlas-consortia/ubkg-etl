# Parameters and order for build_csv.sh / build_csv.py

## Background
Both the UBKG generation framework shell script **build_csv.sh** and the 
Python script **build_csv.py** take
as parameters a set of space-delimited acronyms that identify sets of assertions (onotologies).

Because some ontologies are based on classes that are
defined in other ontologies, the order in which parameters are 
listed can be important.

The content of a particular knowledge base corresponds to the
set of "sets of assertions" used to generate it.

The **-s** command argument directs the script to generate based on previously generated OWLNETS files.
See the uppermost README.md for details.

## Base set of ontologies
All UBKG instances should contain assertions from
the following ontologies:
- UBERON 
- PATO
- CL 
- DOID 
- CCF
- OBI 
- EDAM
- HSAPDV
- SBO 
- MI 
- CHEBI 
- MP 
- ORDO 
- UNIPROTKB 
- UO
- MONDO
- EFO
- AZ

## HubMAP/SenNet ontologies
The HubMAP/SenNet knowledge graph should also include assertions from:

- OBIB 
- XCO 
- HRAVS 
- HUBMAP
- SENNET

## Data Distillery

Instances of the Data Distillery knowledge graph may not necessarily include ontologies specific to HubMAP/SenNET.
A Data Distillery KG **will** include assertions from:


### Glygen ontologies
- FALDO
- UNIPROT (_not to be confused with UNIPROTKB_)
- GLYCORDF
- GLYCOCOO

### SPARC
- NPO

### Others
- LINCS
