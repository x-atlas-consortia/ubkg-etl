# Unified Biomedical Knowledge Graph
## Reactome ingestion script

### Purpose
The scripts in this folder generate files in UBKG edges/nodes format for ingestion of data from [Reactome](https://reactome.org/).

### Scope

Reactome contains information on bilogical pathways. In the Reactome model,
+ *Reactions* are organized into an *event hierarchy*. The event hiearchy is a tree structure that groups reactions into *pathways*.
+ Reactions have molecules as inputs or outputs.
+ Molecules are of two types:
  + *Reference entities*, with invariant properties, and encoded to UniProtKB or CHEBI
  + *Physical entities*, corresponding to *complexes* in Reactome, or combination of molecules

The known use cases for using Reactome data in the UBKG involve relationships between pathways and genes, with genes
being producers of proteins. For this reason, the ingestion of Reactome is limited to relationships between events
(i.e., Reactions and BlackBoxEvents) and reference entities (e.g., proteins).

### Methodology
The ingestion script interrogates Reactome by means of its Content Services API: in particular, the endpoints listed below.
+ https://reactome.org/ContentService/#/events/getEventHierarchy
+ https://reactome.org/ContentService/#/query/findEnhancedObjectById
+ https://reactome.org/ContentService/#/participants/getParticipatingReferenceEntities

### Content
- **reactome.py** does the following:
   - Loops through the set of species specified in the configuration file.
   - Calls endpoints of the Reactome Content Services API.
   - Translates information from endpoints into edges and nodes.

- **reactome.ini.example**: annotated example of an application configuration file.

### File Dependencies
1. Files in the **ubkg_utilities** folder:
   - ubkg_extract.py
   - ubkg_logging.py
   - ubkg_config.py
2. An application configuration file named **reactome.ini.**

### Precursor Assertions
Some Reactome assertions employ nodes from REACTOME_VS, a custom valueset generated from a source file built with the 
SimpleKnowledge framework


#### REACTOME_VS
The responses from the Content Services API include string values that are categorical. To represent these
categorical values with codes, a valueset is necessary. 

The script assumes that REACTOME_VS has been ingested so that its file **OWLNETS_node_metadata.txt** is available.

### To run
Copy and modify **reactome.ini.example** to a file named **reactome.ini** in the reactome directory.

