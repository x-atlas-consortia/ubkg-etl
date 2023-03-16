# Unified Biomedical Knowledge Graph

## ubkg_edges_nodes script

This is currently a placeholder script that allows the generation framework
(build_csv.py) to ingest a set of assertions in the 
"UBKG edges/nodes" format. 

The *ontologies.json* file points to the script; however, 
the assumption is that the edges and nodes files are manually
copied to the owlnets_output folder path. 

The reason for the manual copy is that the initial use case
(Data Distillery) only involves a few sets of assertions.

The script could be enhanced so that it obtains the edges and nodes
files by downloading from a source such as a Globus collection.