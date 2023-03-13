# SimpleKnowledge to OWLNETS converter

Uses the input spreadsheet for the SimpleKnowledge Editor to generate a set of text files that comply with the OWLNETS format, as described in [https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb].

User guide to build the SimpleKnowledge Editor spreadsheet: [https://docs.google.com/document/d/1wjsOzJYRV2FRehX7NQI74ZKRXvH45l0QmClBBF_VypM/edit?usp=sharing]

## Arguments
1. The name of the SimpleKnowledge input spreadsheet for the ontology (e.g., SimpleKnowledgeHuBMAP.xlsx)
2. The name for the ontology.

The script will look for a file in the application directory with a name that matches the first argument.

## Format of SimpleKnowledge Editor spreadsheet

- Column A: term
- Column B: concept code in local ontology
- Column C: definition for concept
- Column D: pipe-delimited list of synonyms
- Column E: pipe-delimited list of references to other ontologies. 

Column F corresponds to an *isa* relationship. 
Columns after F describe custom relationships. 

Each cell in a relationship column contains a comma-delimited list of object concepts that relate.
Each of the object concepts should be defined in a row in the spreadsheet (in column A). 

The SimpleKnowledge spreadsheet's input validation does not capture differences
in case--e.g., if a relationship cell refers to "Abc", when the actual
term is "ABC". The script validates for these cases.

The script loops through each relationship cell in a row and creates a set of subject-predicate-object relationships between the concepts in the cell and the subject concept in column B.