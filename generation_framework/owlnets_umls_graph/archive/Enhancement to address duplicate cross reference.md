# Enhancements to OWLNETS-UMLS-GRAPH to handle duplicate cross-references
October 18, 2022

## Issue
The OWLNETS-UMLS-GRAPH script assumes that the suite of OWLNETS input files 
for an ontology assigns a unique concept for every node in the ontology. 
This includes nodes that are cross-referenced--i.e., have concepts in the
_node_dbxref_ column of the **node-metadata.txt** file.

The MP (Mammalian Phenotype) ontology diverges from the assumed configuration. 
A number of MP nodes (17 as of October 2022) share cross-references to a 
concept from CL (Cell Ontology) that itself associates with one CUI. 

For example, the following MP concepts all cross-reference CL 0000959:
* MP 0009925
* MP 0009926
* MP 0009920
* MP 0009927

Shared cross-references resulted in exceptions in the block of code
that starts with the comment

```# iterate to select one CUI from cuis in row order - we ensure each node_id has its own distinct CUI```
```# each node_id is assigned one CUI distinct from all others' CUIs to ensure no self-reference in edgelist```


This appears to be a rare edge case that has occurred only for a handful of
nodes in one of 10+ ontologies that have been integrated into the ontology graph.

## Solution
For cases in which the script encounters more than one node that 
cross-references a node in another ontology, the script picks a winner. 
It assigns the cross-reference only to the first node of the set that it
encounters. The remaining nodes lose the cross-reference and are mapped
to custom CUIs.
