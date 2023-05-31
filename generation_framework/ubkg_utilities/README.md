# UBKG Utilities

Functions that are common to scripts in the generation framework.

- ubkg_config.py: Functions related to configuration files
- ubkg_extract.py: Functions related to file i/o. In particular, functions in this script wrap various download and Pandas import/export functions with a TQDM progress bar.
- ubkg_logging.py: Functions related to logging
- ubkg_parsetools.py: Functions related to parsing and standardizing column data
- ubkg_subprocess.py: Functions related to calling subprocesses.
- ubkg_reporting.py: A class and functions related to reporting on ingest results.

# ubkg_parsetools - codeReplacements function

The _codeReplacements_ function in **ubkg_parsetools** harmonizes the format of node identifiers from IRIs in edges and nodes files, both in OWLNETS and UBKG Edges/Nodes format.

The UBKG's default format for node identifiers is an IRI that complies with OBO principle 3--i.e.,
it contains a clearly defined namespace (SAB) and code.

An example of an IRI in the expected format is
`http://purl.obolibrary.org/obo/CL_0000990`

This IRI corresponds to CL 0000990.

Some ontologies or sets of assertions use IRIs in different formats. The _codeReplacements_ function
forces a formatting for most of these. The main forms of divergence from the default format are:
1. A number of SABs in the UMLS use alternative formats. This is often done to account for codes that have leading zeroes. The HGNC, GO, and HPO SABs format identifers in the format _SAB_ _SAB_:_code_.
2. Some SABs use idiosyncratic formats. For example, the MONDO ontology identifies genes with HGNC codes, but with an IRI in format `http://identifiers.org/hgnc/code`
3. Some SABs use subdomains that UBKG organizes under a main SAB. For example, the EDAM ontology has subdomains like _topic and _data: UBKG appends "EDAM" to the SAB.

# Turtle files
If an ontology is available only as a Turtle file, it must be converted to RDF/XML for PheKnowLator. 
A Turtle file can separate namespaces by means of **@prefix** statements. If a Turtle file has prefix statements, 
the conversion to RDF/XML will replace references to prefixes with IRIs. In order to 
regain the SABs, it is necessary to re-translate IRIs to prefixes.

The **prefixes.csv** file in this directory contains a set of mappings from Turtle prefixes to SABs.
The initial release of the prefixes file covered the following ontologies:
- GlyCoCoO
- NPO
- NPOSKCAN

# Warning
It is possible that some IRIs will escape formatting. The only way to be sure is to test.

# parsetester.py
The file **parsetester.py** is a small application to test the codeReplacements function in ubkg_parsetools.py. 
The script takes two arguments:
- a SAB corresponding to a set of assertions
- a character that determines whether to check the nodes file or the edges file

The script checks files in the owlnets_output path of the generation_framework.
