# UMLS Concept Data

The [UMLS concept data](https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html) is maintained
by the NLM in a set of flat text files in a special format (RRF).
To obtain updated concept information (especially relationships between concept CUIs):
1. Download and unpack the RRF files using an application named [MetamorphoSys](https://www.ncbi.nlm.nih.gov/books/NBK9683/)
2. Upsert the ontology data (concepts and relationships) into [Neptune](https://ieeexplore.ieee.org/abstract/document/938063)
3. Export the UMLS specific data from Neptune into CSV files.

The entire UMLS set of vocabularies is refreshed at least quarterly.

Some constituent vocabularies (e.g., RxNORM) are refreshed weekly.

Thus, the CSV extract from Neptune establishes the currency (initial set of .csv files) of the ontology build.
The nodes and relationships in our [Neo4J](https://neo4j.com/) graph will only be as current as are the relationships in the source UMLS (above) data.

You pull a copy of the UMLS CSVs from Neptune and use them in the "Jonathan" script.
That script uses both the UMLS CSVs and the [OWLNETS](https://github.com/callahantiff/owl-nets) TSVs (extrated from OWL files) to generate a new set of custom ontology CSVs
that can then be imported into a new Neo4J graph.
You can also use the output CSVs as the input to this process to create another set of CSVs that contain relationships
found in the input CSVs as well as the input OWLNETS TSVs. In this manner, you iteratively add OWL relationships to the CSVs.

You could generate a new neo4j just from the UMLS CSVs. However, it would only contain data on the ontologies that are managed directly by the UMLS.
The OWLNETS TSV files enhance the UMLS ontology data.

The final iteration output CSVs are used as input to the creation of the Neo4J database, and are
imported using [neo4j-admin import](https://neo4j.com/docs/operations-manual/current/tools/neo4j-admin/neo4j-admin-import/)
found in the Neo4J [Docker file](https://github.com/hubmapconsortium/ontology-api/blob/main/neo4j/Dockerfile).
