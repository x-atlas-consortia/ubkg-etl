# SimpleKnowledge to OWLNETS converter

Uses the input spreadsheet for the SimpleKnowledge Editor to generate a set of text files that comply with the OWLNETS format, as described [here](https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb).

The user guide to build the SimpleKnowledge Editor spreadsheet can be found [here](https://github.com/x-atlas-consortia/SimpleKnowledge/blob/main/doc/EditorUserGuide.md).

# Content
- **skowlnets.py** - Does the following:
   - Reads a configuration file.
   - Downloads the SimpleKnowledge spreadsheet that corresponds to the SAB argument.
   - Generates files in OWLNETS format based on the spreadsheet.
- **skowlnets.ini.example** - Annotated example of an ini file.

# Configuration file and SimpleKnowledge source spreadsheets
The SimpleKnowledge spreadsheets that **skowlnets.py** uses are located in the **scr** folder of the [SimpleKnowledge](https://github.com/x-atlas-consortia/SimpleKnowledge/tree/main) GitHub repository.

# Arguments
1. The SAB for the ontology--e.g., HUBMAP, SENNET, AZ

# Dependencies
1. Files in the **ubkg_utilities** folder:
   - ubkg_extract.py
   - ubkg_logging.py
   - ubkg_config.py
   - ubkg_parsetools.py
2. An application configuration file named **gencode.ini.**
3. A spreadsheet in SimpleKnowledge format stored as a Google Sheets document.

# To run
1. Copy and modify **skowlnets.ini.example** to a file named **skowlnets.ini** in the current directory.
2. Configure the **ontologies.json** file at the generation_framework root to call skowlnets.py with the appropriate SAB.


# Format of SimpleKnowledge Editor spreadsheet

- **Column A**: term
- **Column B**: concept code in local ontology
- **Column C**: definition for concept
- **Column D**: pipe-delimited list of synonyms
- **Column E**: pipe-delimited list of references to other ontologies. 

**Column F** corresponds to an *isa* relationship. 
Columns after **Column F** describe custom relationships. 

Each cell in a relationship column contains a comma-delimited list of object concepts that relate.
Each of the object concepts should be defined in a row in the spreadsheet (in **Column A**). 

The SimpleKnowledge spreadsheet's input validation does not capture differences
in case--e.g., if a relationship cell refers to "Abc", when the actual
term is "ABC". The script validates for these cases.

The script loops through each relationship cell in a row and creates a set of subject-predicate-object relationships between the concepts in the cell and the subject concept in column B.