# Parameters and order for build_csv.sh / build_csv.py

## Background
Both the UBKG generation framework shell script **build_csv.sh** and the 
Python script **build_csv.py** take
as parameters a set of space-delimited acronyms that identify sets of assertions (onotologies).

Because some ontologies are based on classes that are
defined in other ontologies, the order in which parameters are 
listed can be important.

The **UBKG context** of a particular UBKG instance corresponds to the
ordered set of "sets of assertions" used to generate it.

# contexts.ini
UBKG contexts can be specified with an optional file named **contexts.ini**. 
The contexts.ini file should contain sections for:

- a [Base Context] section, with a context name of base
- a [Contexts] section, for which each value is the name of a context and a set of additional SABs

Each value in the INI file should be a space-separated list of SABs--e.g., 
```
[Contexts]
hmsn=OBIB XCO HRAVS HUBMAP SENNET
```

## Base context
All UBKG instances should contain assertions from
the following ontologies:
- UBERON 
- PATO
- CL 
- DOID
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
- AZ (Azimuth)

## HubMAP/SenNet context
The HubMAP/SenNet knowledge graph should also include assertions from:

- OBIB 
- XCO 
- HRAVS 
- HUBMAP
- SENNET

## Data Distillery context

Instances of the Data Distillery knowledge graph may not necessarily include ontologies specific to HubMAP/SenNET.
A Data Distillery KG **will** include assertions from:

### Glygen ontologies
- FALDO
- UNIPROT (_not to be confused with UNIPROTKB_)
- GLYCORDF
- GLYCOCOO

### SPARC
- NPO (NPOKB)
- NPOSKCAN

### GTEX
- GTEX_COEXP
- GTEX_EQTL
- GTEX_EXP

### Others
- LINCS
