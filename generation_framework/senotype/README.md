# Unified Biomedical Knowledge Graph
## Senotype ingestion script

### Purpose
The script in this folder generates files in UBKG edges/nodes format for ingestion of data from Senotype.

### Content
**senotype.py** does the following:
- Obtains configuration information from a file named **senotype.ini** in the application directory.
- Reads Senotype submission files in JSON format from the [senlib](https://github.com/sennetconsortium/senlib) GitHub repository
- Consolidates submission file information into edge and node files in UBKG edge/node format.

### Node data
The script calls external sources to obtain node information, including:
1. NCBI EUtils for titles of articles referenced by PubMed ID
2. The SciCrunch resolver for descriptions of RRIDs
3. The SenNet entity-api for titles of datasets

### senotype.ini
The **senotype.ini** file includes a SenNet Globus token.

## Post processing of CODEs.csv
The **senotype.py** script adds content to the _firstname_, _lastname_, and _email_ columns for Senotype code nodes. 
These three columns are only populated for a few codes in CODEs.csv.

To correct column issues in CODEs.csv for neo4j import, run the **csv_column_checker** script.