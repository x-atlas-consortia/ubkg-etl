# Unified Biomedical Knowledge Graph (UBKG)
## Source and Generation Framework Scripts

Scripts in this repo compose the following components of the 
UBKG:

### Source Framework
The source framework
- extracts from a data warehouse assertion data from the UMLS
- formats output as CSVs for import into a neo4j knowledge graph

UMLS data is obtained from releases of the UMLS in 
Rich Release Format. The University of Pittsburgh's 
Department of Biomedical Informatics maintains the data warehouse
that the source framework uses.

### Generation framework
The generation framework is a suite of Extract-Transform-Load (ETL)
scripts that
- extract assertion data from sources, including OWL files
- appends assertions to the set of UMLS CSVs

## Additional information

For more information on the UBKG, consult the [GitHub Docs site](https://github.com/x-atlas-consortia/ubkg-docs).