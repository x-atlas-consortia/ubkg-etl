# Enhancements to OWLNETS-UMLS-GRAPH to remove dependency on OWLNETS_relations.txt
November 14, 2022

# Issue
The OWLNETS-UMLS-GRAPH script assumes the presence of 3 files that are the output of the PheKnowLator-based OWL-OWLNETS converter:

- **OWLNETS_edges.txt**: triples from the ontology
- **OWLNETS_node_metada.txt**: details on the nodes (subject, object) in the triples
- **OWLNETS_relations.txt**: details on the predicates of the triples

We recently started the Data Distillery (DD) project. We agreed to use a single code base for the ontology generation framework--i.e., 
ontology graphs for DD, Unified Biomedical Knowledge Graph (UBKG), HuBMAP, SenNet, etc. would be generated identically.

For DD, we specified only two files:

- **edges.tsv**, corresponding to OWLNETS_edges.txt
- **nodes.tsv**, corresponding to OWLNETS_node_metadata.txt

The assumption was that the information in OWLNETS_relations.txt was redundant, and could be derived from the _predicate_ field of OWLNETS_edges.txt.

# Solution
It was necessary to modify the OWLNETS-UMLS-GRAPH script so that it does not depend exclusively on the relations 
file to obtain relationship information. The script now relies more on
a source file of information from the Relations Ontology (RO).

# Unintended consequences that needed to be addressed

1. Information in the relations file is **not redundant** for the case in which the relationship is defined with an IRI from an ontology other than the Relationship Ontology. The script currently obtains all relationship information from RO, including names of relationships; thus, it is not possible to obtain a relationship label for a relationship identified with an IRI not in RO except by means of the relationship file. As this is a common case for ontologies processed by PheKnowLator, we must allow the script to continue to use the relations text if it is available.
2. If the relations file is not present, the script's dependency on the Relations Ontology source (ro.json) is greater, especially with respect to inverse relationships. 

# Improved accuracy of relationship data
Increasing the dependency on the current source of information for RO (ro.json) required the 
addressing of two types of flaws in ro.json:

1. Some relations do not have inverses. The script creates a "pseudo-inverse" in the form of a relationship with prefix "inverse_". (The earlier script also did this, but missed some relationships.)
2. Some relations had incomplete information regarding their inverses.
For example, RO_0002206 (expressed in) is listed as the inverse of RO_0002292 (expresses), 
but RO_0002292 is not listed as the corresponding inverse of RO_0002206. The script can now identify the appropriate inverse relationship instead of just creating a pseudo-inverse.