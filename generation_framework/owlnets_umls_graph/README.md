
# OWLNETS to CSV conversion script

# Scope
This script:
* Obtains data for a source from triple store information in OWLNETS format
* Appends data from the source to the ontology CSVS that will be loaded into a neo4j instance of UBKG

This script is referred to as "Jonathan's" script in references in build_csv.py.

# Location in ingestion workflow
This script is invoked as a subprocess by the **build_csv.py** script that implements the ingestion workflow.
Before invoking this script,  **build_csv.py** obtains assertion data for a data source (e.g., OWL, FTP, or files
downloaded from Globus) and builds a set of assertion files in OWLNETS format.

# Arguments
**build_csv.py** passes the following arguments to this script:
1. the path to a folder on the local machine that contains the 12 ontology CSVs of UBKG content
2. the path to a set of files in OWLNETS format that corresponds to assertion data from a data source
3. the Source ABbreviation (SAB) for the data source

# Ingestion algorithm
## Objectives
The OWLNETS-CSV script integrates information from a data source into a set of ontology CSVs. Integration includes:
1. Adding new nodes corresponding to codes in the data source.
2. Adding new relationships corresponding to assertions in the data source.
3. Cross-referencing codes from the data source to UBKG concepts.

## Files and formats
The OWLNETS-CSV script can work with files in the following formats:
1. The [OWLNETS](https://github.com/callahantiff/PheKnowLator/wiki/OWL-NETS-2.0) format that the PheKnowLator application generates from an OWL source
2. The UBKG [Edge/Node](https://ubkg.docs.xconsortia.org/formats/#ubkg-edgesnodes-format) format.

## Node (entity) creation

The required format for node identifiers (_CodeId) of nodes in the UBKG is _SAB_:_CODE_, where _SAB_ is the 
Source ABbreviation for the code's vocabulary and _CODE_ is the code for the entity in the vocabulary.

Many data sources uses IRIs to describe codes. As described in the [UBKG documentation](https://ubkg.docs.xconsortia.org/formats/#requirements-for-nodes), the 
conversion script is optimized to work with IRIs that comform to OBO principle 3--e.g,
http://purl.obolibrary.org/obo/UBERON_0004086

The conversion script can work with simpler representations of codes, such as 
_SAB_ _delimiter_ _code
in which _delimiter_ can be a colon, underscore, or space

Because data sources vary widely in how they represent the entities in assertions, the conversion script employs a complicated
parsing logic in the function _codeReplacements_ in the **ubkg_parsetools.py** module of the _ubkg_utilities_ folder of this repo.

The parsing logic translates codes from sources that are known not to conform to UBKG expectations. A simple example of a translation
is that of codes from the GO ontology in UMLS, which are represented in UMLS as GO:GO _code_ but are represented in the UBKG as 
GO:_code_.

## Node inclusion
In general, a data source will assert relationships that involve codes from other 
vocabularies (or _foreign nodes_). The conversion script attempts to build content for 
all nodes in a data source's set of assertions--i.e., in the edge file.

A node defined in an assertion in an edge file can be one of two types. The conversion 
script handles each type differently:
1. The node appears both in the edge file and in the node file. This is the usual case for the output of PheKnowLator.
2. The node appears in the edge file, but not in the node file. This is often the case for custom edge and node files such as from Data Distillery.

If the node is not defined in the edge file, the conversion script will assume that it was
defined in a previous ingestion, and is already in the CODES.CSV file. If the node was not 
defined in a previous ingestion, any assertions in the new data source involving the node will not be ingested into the ontology CSVs.

## Node code-concept links 

The conversion script's most complex tasks involve linking codes to UBKG concepts. Because the most important feature of the UBKG 
is [code synonymy](https://ubkg.docs.xconsortia.org/datamodel/#concepts-and-synonymy), the conversion script attempts to link 
a code to an existing CUI when possible--preferably, a _unique_ CUI from the UMLS.

### Cross-referencing
The CUI assignment logic is complicated by cross-references (also known as _dbxrefs_). A data source can define a cross-reference for a code
in the **node_dbxref** column of the node file. A code can have multiple cross-references, either indirectly to codes in other vocabularies or
directly to UMLS CUIs.

Cross-referencing in the UBKG is _transitive_, because the goal of the UBKG is to establish code synonymy.
If a code has a cross-reference to a second code that is itself cross-referenced, both codes will share the same CUI. 

For example, consider the code SAB1:Code1 that is cross-referenced to code SAB2:Code2. If SAB2:Code2 is linked to a
concept with CUI=CUI3, then both SAB1:Code1 and SAB2:Code2 will link to CUI3. However, if SAB2:Code2 is
itself cross-referenced to a code SAB3:Code3 that is linked to a concept with CUI=4, then all three codes will link to CUI4.

#### cross-reference format

The dbxrefs column is, in general, a string in format
_SAB_ _SAB-CODE delimiter_ _CODE_ _CODE-CODE delimiter_...
e.g., SAB1:Code1|SAB2:Code2. The accepted CODE-CODE delimiter is a pipe; the SAB-CODE delimiter can be either a colon or a space.

The members of the dbxrefs column are assumed to be in the data source's order of preference.

#### Code-CUI mapping and "preferred CUI"

Before assigning the codes from the SAB to ingest to CUIs, the script reads the file CUI-CODES.CSV of the concept-code assignments that existed
prior to the current ingestion. The script inverts the information to build 
a DataFrame of prior code-concept assignments.

To assign a code to one or more concepts, the conversion script does the following:

1. Converts the delimited string of cross-references for the code from **node_dbxrefs** to an array of cross-references.
2. Weights code-CUI assignments according to the following order of preference:
   - the set of UMLS CUIs for a cross-referenced code that existed in CUI_CODES.csv prior to the current ingestion
   - the set of UMLS CUIs for the code that existed prior to the current ingestion
   - the set of non-UMLS CUI for a cross-referenced code that existed in CUI_CODES.csv prior to the current ingestion
   - a new, custom CUI for the code in format _SAB_:_CODE_ CUI
3. Creates a unique list of CUIs ordered according both to weighting and to order in the original dbxref column.

In general, a CUI will be linked to multiple codes. The conversion script attempts to define a 
"preferred concept" for the code--i.e., a link with 
CUI that has not already been assigned to another code in the nodes file. 

The script will also link the code to all of the other CUIs in the ordered list. However,
the script will identify the "preferred concept" by means of the CUI property on the "preferred term"
relationship--i.e., the Term node with a relationship of type "PT" with the code. 

This form of identification is, unfortunately, not obvious. However, when a Cypher query
involving Concept-Code-Term paths in the UBKG results in duplicates because of multiple CUI-code
assignments, filtering on the CUI property between the Code and Term nodes usually resolves duplicates.

## Node terms
UBKG codes from the UMLS can have terms from a variety of term types. Codes from non-UMLS data sources, on the other
hand, will only have preferred terms (from the **node_label** column of the node file) 
or synonyms (from **node_synonyms**.)

The script attempts to define Term nodes of either _PT_ (for preferred term) or
_SYN_ for synonym.

### PT_SAB
In general, a data source will refer to nodes from other data sources--e.g.,
UBERON asserts relationships between UBERON codes and PATO codes.

The node file for a data source may include information on nodes that are from another data source.
In some cases, a data source may define a preferred term for a node from another vocabulary
that differs from the preferred term that the other vocabulary defines. For example,
UBERON may define a term of "knees" for a PATO code that uses "knee".

The UBKG allows the preferred term for a code from a vocabulary to be defined only by 
that vocabulary. For preferred terms from other vocabularies, the conversion script
creates terms of type PT_SAB, where SAB refers to the vocabulary defining the term.
In the example above, the preferred term of "knees" for a PATO code as defined by UBERON
would be assigned a type of PT_UBERON.

## Edge (relationship) creation
The ideal form for an assertion's predicate in a data source is an [IRI](https://en.wikipedia.org/wiki/Internationalized_Resource_Identifier) for an entity in the 
**Relationship Ontology** (RO) that has a distinct inverse relationship defined in the same ontology. Predicates in this format are more likely to be standard.

An example of an ideal relationship is 
http://purl.obolibrary.org/obo/RO_0000052, _characteristic_of_, with inverse relationship http://purl.obolibrary.org/obo/RO_0000053 (_has_characteristic_)

Although most [OBO](https://obofoundry.org/) compliant data sources ingested into UBKG encode assertion relationships with RO IRIs, many sources use alternative representations, including:
- IRIs for ontologies other than RO
- unencoded terms (text strings)

In addition, many relationship terms from sources other than RO do not conform to neo4j expectations for relationship labels. Problems include:
- characters other than alphanumeric characters or the underscore--e.g., dashes
- a number as the first character

Finally, sources assert hierarchical relationships with a variety of relationships; however, the UBKG adopts the UMLS standard of using _isa_. 

The script converts assertion predicates into labels for relationships in UBKG as follows:
1. Obtains the term for the edge with the following order of preference:
   - if the predicate is an IRI to a code in RO, the term for the code in RO
   - if the predicate is a simplified IRI in format RO:_code_, the term for the code in RO
   - if the predicate is a string that exactly matches the term of a code in RO, the term for the code in RO
   - if the source files are from a PheKnowLator conversion, the label for the relationship in the OWLNETS_relations.txt file
   - the string for the predicate from the edge file
2. Translates the characters of the relationship label to comply with UBKG standards, including:
   - casting to lowercase
   - replacing with underscore characters all characters except alphanumeric characters and the underscore
   - pre-pending **rel_** to labels that begin with a numeric character
3. Translates hierarchical relations (e.g., _type_) to _isa_.

### Inverse relationships
The principal benefit of using the Relationship Ontology is that RO defines inverse relationships for most of its entities. 
If the conversion script can find an edge assertion predicate in RO, it will attempt to derive the inverse releationship from RO itself. 
If either RO does not identify an inverse relationship or the script cannot link the relationship to a RO entity, the script will
create a default inverse relationship by prepending _inverse__ to the relationship label.

# Output

After completing analysis of content from the input files, the script
appends content to the existing set of ontology CSVs.


# Miscellaneous
## Archive folder
In earlier iterations of development, the OWLNETS-UMLS-GRAPH script was developed as a Jupyter notebook and then converted
to a pure Python script by means of the **transform.py** script.

The script was versioned by incrementing a number at the end of the filename.

Earlier versions of this script, along with the transform script, are in the Archive folder.

## Ingestion summary report

The script generates a summary report of quality statistics related to ingestion.

Information includes:
1. Counts of the unique nodes in the edge file by SAB. These counts may help to identify SABs that should be ingested prior to the current SAB.
2. Counts of nodes in the edge file that are not also in the nodes file. Nodes that are in the edge file, but not the node file, will be ingested only if they already exist in the onotology CSVs.
3. Counts of the unique predicates in the edge file. These counts may help to identify predicates that should be associated with IRIs in the Relations Ontology.
4. Counts of the unique dbxrefs in the node file, by SAB. This may identify SABs that should be ingested prior to current SAB.
5. SABs for dbxrefs that are not in the final CODEs.csv. Cross-references with SABs that are not in CODEs.csv will not be established: nodes with these dbxrefs will likely be assigned a custom CUI.

