# Unified Biomedical Knowledge Graph
## RefSeq summary ingestion script

### Purpose
The script in this folder import gene summaries from RefSeq, linking to Entrez ID.

### Content
- **refseq.py** does the following:
   - Calls the **esearch** and **esummary** endpoints of the NCBI [eUtils](https://www.ncbi.nlm.nih.gov/books/NBK25497/) REST API.
   - Obtains summary information for all human genes in NCBI Gene.
   - Appends summaries as Definition nodes in the UBKG ontology CSVs.
-  **refseq.ini.example**: annotated example of an INI file
-  **apikey.txt.example**: example of a file that contains a NCBI API key

### File Dependencies
1. Files in the **ubkg_utilities** folder:
   - ubkg_extract.py
   - ubkg_logging.py
   - ubkg_config.py
   - ubkg_apikey.py
2. An application configuration file named **refseq.ini.**
3. A file named **apikey.txt** that contains a NCBI API key.

### Precursor Assertions
GenCode should be ingested into the UBKG ontology CSVs before running refseq.py.
The Entrez IDs to which refseq links gene summaries come from GenCode.

### To run
- Copy and modify **refseq.ini.example** to a file named **refseq.ini** in the gencode directory.
- Copy and modify **apikey.txt.example** to a file named **apikey.txt**. The file should contain a NCBI API key.

