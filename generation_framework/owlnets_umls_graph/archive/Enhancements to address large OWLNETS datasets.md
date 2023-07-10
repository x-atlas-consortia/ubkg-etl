# Enhancements to handle large OWLNETS datasets
October 20, 2022

## Issue
The PR ontology generates a set of very large OWLNETS files. 
Because the OWLNETS-UMLS-GRAPH.py script currently operates completely
in memory using Pandas, extremely large files can result in MemoryError 
exceptions. These errors are "silent" in that they simply cause the 
script to terminate without notification.

## Solution
For the PR ontology, it is fortunate that proteins are generally 
associated with an organism--e.g., with strings like "human" in the
description. As an admittedly crude filter, the script filters the
**node_metada.txt** and **edgelist.txt** files to only those proteins
that are unambiguously for a specified organism.

An optional parameter (-p) allows the calling script to specify the organism.

This filtering method allows the script to reduce the number of 
proteins in PR from over 360K to around 100K, bringing processing
within memory constraints.
