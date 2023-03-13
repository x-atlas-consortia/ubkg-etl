# Enhancements to OWLNETS-UMLS-GRAPH for HUSAT and UNIPROTKB
October 12, 2022

## Background
The application architecture that supports the HuBMAP ontology service includes a knowledge graph representing a polyhierarchical organization of interconnected ontologies. The knowledge graph is based on an export from the UMLS Metathesaurus, which manages the majority of the standard ontologies and vocabularies in the system. The distinctive feature of the HubMAP ontology is that it extends the UMLS knowledge by integrating concepts from other ontologies. In particular, the ontology includes information from sources such as:
Ontologies that are not in UMLS, but published in other sources such as the OBO Foundry and the NCBO BioPortal
Custom application ontologies, such as the ontology built for HuBMAP configuration information
Data sources that can be represented as ontologies, such as the UniProtKB protein database.

The architecture to generate the source for the ontology graph includes a number of scripts, the most important of which is OWLNETS-UMLS-GRAPH.py. This script integrates data from “non-UMLS” ontologies into the larger ontology graph and establishes links between concepts in the “non-UMLS” ontologies and other concepts in the ontology graph.
New use cases
The OWLNETS-based architecture has succesfully integrated a number of ontologies into the knowledge graph, including OBI, UBERON, ORO, and CHEBI. Recent work to integrate ontologies for HUBMAP, HUSAT (HuBMAP Samples Added Terms), and UNIPROTKB  exposed issues that required four enhancements to the architecture, especially the OWLNETS-UMLS-GRAPH script. 

## Enhancement 1: special handling of HGNC nodes
### Issue
In general, a concept from an ontology is identified with an alphanumeric string in format 
_SAB_{_Delimiter_}{_Code_}, in which
* _SAB_ (the Source Abbreviation in UMLS) is a string that identifies the source vocabulary. In the parlance of the PheKnowLator scripts that the architecture employs, the SAB would be the namespace for an ontology. Examples of SABs are UMLS, SNOMEDCT_US, NCI, and HUBMAP.
* _Delimiter_ is a single character in the character set {colon; underscore; space}. 
* _Code_ is an alphanumeric identifier for the concept in the source vocabulary:
For UMLS, Code corresponds to the UMLS Concept Unique Identifier (CUI).
For other ontologies, Code corresponds to a code.

The OWLNETS-UMLS-GRAPH can usually convert incoming code strings to align them with the corresponding codes in the knowledge graph. For example, the script can convert either “UMLS C00000” or “UMLS:C00000” to the standard “UMLS C00000”.

In contrast to other ontologies, HGNC concepts are stored in the graph with strings that contain two of the three delimiters. 
The format for a gene concept in HGNC is _HGNC HGNC: Code_. Processing a HGNC code with the standard algorithm results in strings like “HGNC: HGNC HGNC: HGNC x” or “HGNC HGNC x”, neither of which align with the codes in the graph.
### Solution

To date, HGNC is the only ontology that presents a challenge to code alignment. Two of the ways to address this include:
1. Formatting incoming HGNC codes so that they emerge from the text conversion in the desired format–i.e., gaming the text conversion.
1. Ignoring the text conversion and assuming that incoming HGNC codes are properly formatted.
In either option, the OWLNETS-UMLS-GRAPH has to be modified to account for the edge case of HGNC. The second approach is more stable.

## Enhancement 2: Handling mixed case codes for cross-referencing
### Issue
Prior to the integration of  HUSAT, codes for ontologies were either numbers or uppercase strings. HUSAT’s codes are mixed case strings. As part of establishing cross-references (equivalence classes), the OWLNETS-UMLS-GRAPH converted the strings for codes in node_metadata.txt to uppercase before comparing them against the graph’s concept source (CUI_CODEs.csv). If the comparison is case-sensitive, codes in mixed case were ignored.

### Solution
Comparisons between data in node_metadata.txt and CUI_CODEs were made case-insensitive.

## Enhancement 3 : Finding all inverse relationships in RO
### Issue
To establish bidirectional relationships between nodes, the OWLNETS-UMLS-GRAPH script uses a [JSON](https://raw.githubusercontent.com/oborel/obo-relations/master/ro.json) downloaded from 
the Relations Ontology (RO) to identify potential inverse relationships. 
For example, if a node has a relationship of _expresses_ with another node, the script can 
identify the inverse relationship _is expressed by_.

Prior to the integration of UNIPROTKB, it was possible to identify the inverse 
for relevant relationship properties in the RO by means of the “inverse of” key in the **nodes** array, or perhaps by 
looking for “inverse” in the property term. The only relationship property that is used in the initial release of 
UNIPROTKB, _has gene product_, did not conform to this format, so the script was unable to establish expected 
relationships between nodes in UNIPROTKB and nodes in HGNC.

### Solution
Inverse relations are defined consistently and explicitly in the **edges** array of RO.json. 
This element, for example, shows that the RO property _gene product_ of
(RO_0002204) has the inverse property of _has gene product_ (RO_0002205):

`{
    "sub" : "http://purl.obolibrary.org/obo/RO_0002204",
    "pred" : "inverseOf",
    "obj" : "http://purl.obolibrary.org/obo/RO_0002205"
}`

Using the **edges** array to identify inverse relationships gives more accurate results than using the “inverseOf” key 
in the **nodes** array. As [this comparison](https://docs.google.com/spreadsheets/d/1t1eiAgxi8HB2xTEEdMPl81o_Ri2XICVvkVZKTYSfKKw/edit?usp=sharing) shows, 
the new method identifies all of the inverse relationships identified by the old method; however, it also identifies a large number of other valid inverse relationships, such as the ones needed for UNIPROTKB.

Another benefit of the newer method is that it does not rely on the presence of the term “inverse” in a relationship property term.

## Enhancement 4: Using nodes from external ontologies as object nodes
### Issue
Prior to the integration of UNIPROTKB, it was possible to use only the OWLNETS_edgelist.txt and OWLNETS_node-metadata.txt files to establish relationships between nodes in an ontology such as subClassOf (isa). The OWLNETS-UMLS-GRAPH script assumed that both the subject nodes and object nodes of all triples in the ontology were defined in the node metadata file: if edgelist showed a relationship between node A and node B, there were rows for both nodes in node-metadata. 

The exception to this was for equivalence classes or cross references, identified via the dbxrefs column of node-metadata. 

Unlike other ontologies, the UNIPROTKB OWLNETS files defined relationships between UNIPROTKB codes and HGNC codes in the edgelist file, but only identified UNIPROTKB nodes in the node-metadata file. Because the HGNC codes were not in the node-metadata file, the script could not establish relationships in which the HGNC codes were the object nodes.

Adding the HGNC codes as nodes in the node-metadata file was not a solution: when the nodes were in the file, the script generated spurious versions of the HGNC codes to which to link the UNIPROTKB nodes.

### Solution
Methods from the dbxref logic were applied to object nodes.

An _object node_ is the node to the right of 
a predicate in a _subject node_ - _predicate_ - _object node_ relationship. 

In general, an object node for a node in edgelist can be one of two types:
1. A node in the ontology, or _internal object node_–e.g., HUBMAP_C00002 isa HUBMAP_C00001. Internal object nodes are defined in the node metadata.
1. A node in another ontology, or _external object node_–e.g., UNIPROTKB_X gene product of HGNC HGNC: Y. External object nodes are not defined in the node metadata, but may already be defined in the graph (CUI-CODEs.CSV).

It is assumed that an object node is only of one type.

In general, a set of subject nodes in the edgelist may have relationships with object nodes of both types, so it is necessary to check both for internal and external references.

The enhanced code:
1. Compares object nodes with both the node metadata file and CUI-CODEs.
2. Associates the appropriate CUI with the object node:
- The CUI that the script derives for the node from the information in the node metada file.
- The CUI from CUI-CODEs.

