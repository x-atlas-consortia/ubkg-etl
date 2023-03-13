# NOTE
This README.md contains references to other documentation in markdown files. In some cases, this documentation is for an earlier prototype deployment.

## Framework
The following image describes the current source framework. The operation of the framework is also described in the general README.md for UBKG.

DBMI's process for exrtracting source data from the UMLS is described [here](https://github.com/dbmi-pitt/ubkg/blob/main/source_framework/UMLS%20Extraction%20Process.md).

![Source_framework](https://user-images.githubusercontent.com/10928372/202453373-6e2f73ba-e7ae-4d8f-9ece-31b0b0732a74.jpg)


# UMLS-Graph 
This corresponds to the set of **UMLS CSVs** that can be used to generate a knowledge graph of the UMLS.

UMLS Graph database for semantic queries.

This project extracts from UMLS Metathesauras and Semantic Network files in Oracle, transforms, loads, deploys, and queries the resulting neo4j knowledge graph.
It uses the conceptual model pictured here:

![Alt text](UMLS-Graph-Model.jpg?raw=true "Title")

The **starting point** of this repository is the UMLS active subset distribution loaded into Oracle.
The **ending point** of this repository (what it functionally creates) is a live neo4j database of the UMLS active subset, including:
- English **terms** (including preferred terms and synonyms)
- **Codes** (including NDC Codes with the SAB {_Source Abbreviation_}  **NDC**)
- **Concepts** 
- **Semantic Types**
- **Definitions** 

Refer to the conceptual model in the following illustration.

An early prototype of the UMLS graph database is deployed in a Docker container on Amazon Web Services with a UI at [Guesdt.com](https://guesdt.com/).

## UMLS MetamorphoSys configuration
The [MetamorphoSys](https://www.nlm.nih.gov/research/umls/implementation_resources/metamorphosys/help.html#starting) application is used to download data from both the UMLS Metathesaurus and the Semantic Network.

## CSV-Extracts
[**CSV-Extracts.md**](https://github.com/dbmi-pitt/UBKG/blob/main/Source_framework/CSV-Extracts.md) contains descriptions of and the SQL to generate each of the CSV files from UMLS active subset in Oracle. This file also contains the neo4j database import load script which reads the CSV files and loads them into neo4j. Note this has only been tested on the community edition running from neo4j's unix tar distribution on Mac OSX. A roughly equivalent but better Jupyter Notebook for the SQL extracts is also in this repository (not including the neo4j loads or index calls).

## Graph-Query-Examples
[**Graph-Query-Examples.md**](https://github.com/dbmi-pitt/UBKG/blob/main/Source_framework/Graph-Query-Examples.md) contains example useful Cypher queries for the complete UMLS-Graph database running in neo4j.

Update: Access to the UBKG knowledge graph information will be mediated by a REST API that will encapsulate Cypher queries.

## Graph-Deploy-AWS
[**Graph-Deploy-AWS.md**](https://github.com/dbmi-pitt/UBKG/blob/main/Source_framework/Graph-Deploy-AWS.md) contains implementation instructions to build a Docker version of UMLS-Graph on an AWS EC2 instance (minimum 4 GB memory recommended).  This is not the deployment for the UBKG, but for the UMLS-only prototype.

## UI Javascript code
Guesdt-X.X.X.html is the UI code deployed at guesdt.com after login.
