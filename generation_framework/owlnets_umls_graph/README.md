
# OWLNETS to CSV conversion script

This script:
* Obtains data from triple store information in OWLNETS format
* Appends data into the ontology CSVS that can be loaded into the UBKG neo4j database

This script is still referred to as "Jonathan's" script in references in build_csv.py.

## Archive folder
In earlier iterations of development, the OWLNETS-UMLS-GRAPH script was developed as a Jupyter notebook and then converted
to a pure Python script by means of the **transform.py** script.

The script was versioned by incrementing a number at the end of the filename.

Earlier versions of this script, along with the transform script, are in the Archive folder.

## Ingest summary report

The script generates a summary report of quality statistics related to ingestion.

Information includes:
1. Counts of the unique nodes in the edge file by SAB. These counts may help to identify SABs that should be ingested prior to the current SAB.
2. Counts of nodes in the edge file that are not also in the nodes file. Nodes that are in the edge file, but not the node file, will be ingested only if they already exist in the onotology CSVs.
3. Counts of the unique predicates in the edge file. These counts may help to identify predicates that should be associated with IRIs in the Relations Ontology.
4. Counts of the unique dbxrefs in the node file, by SAB. This may identify SABs that should be ingested prior to current SAB.
5. SABs for dbxrefs that are not in the final CODEs.csv. Cross-references with SABs that are not in CODEs.csv will not be established: nodes with these dbxrefs will likely be assigned a custom CUI.
