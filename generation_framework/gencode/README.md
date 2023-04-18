# Unified Biomedical Knowledge Graph
## GenCode script

# Purpose
The scripts in this folder generate files in UBKG edges/nodes format for ingestion of data from GenCode.

# Content
- **gencode.py** does the following:
  - downloads GZIPped files from the GenCode FTP site, including:
     - the main annotation file
     - metadata files for 
        - Entrez Gene
        - RefSeq
        - UniProt/SwissProt
        - UniProt/TrEMBL
  - expands GZIP files to GTF files.
  - translates the annotation file by:
    - extracting and collecting values from the key-value column (9th column)
    - merging with the metadata files 
  - filters annotation output based on indications in the configuration file.
  - _TO DO_ using the translated annotation data to build edges and nodes files.
- **gencode.ini**: configuration (INI) file.
- **gencode.ini.example**: annotated example of gencode.ini.

   Contains a list of URLs to download from the GenCode FTP site.

# Dependencies
Files in the **ubkg_utilities** folder:
- ubkg_extract.py
- ubkg_logging.py
- ubkg_config.py
