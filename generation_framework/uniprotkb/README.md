# UNIPROT KB to OWLNETS converter

Converts to OWLNETS format (described [here](https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb]))
data obtained from [UniProt.org](https://www.uniprot.org/).

# Content
- **uniprotkb.py** - Does the following:
   - Reads a configuration file.
   - Submits a query to the UniprotKB REST API that returns data similar to that available [here](https://www.uniprot.org/uniprotkb?query=).
   - Downloads a file of HGNC codes from [genenames.org](https://www.genenames.org/download/custom/)
   - Generates files in OWLNETS format based on the data from UNIPROTKB and HGNC.
- **uniprotkb.ini.example** - Annotated example of an ini file.

# Dependencies
1. Files in the **ubkg_utilities** folder:
   - ubkg_extract.py
   - ubkg_logging.py
   - ubkg_config.py
2. An application configuration file named **uniprotkb.ini.**

# To run
1. Copy and modify **uniprotkb.ini.example** to a file named **uniprotkb.ini** in the current directory.

# Background

It is possible to obtain data from [UniProt.org](https://www.uniprot.org/uniprotkb?query=*) by executing a call to the **stream** endpoint of UniProt's REST API. 
For the purposes of the UBKG, the relevant information from UniProtKB is:
1. UniProtDB entry (e.g., AOA0C5B5G6)
2. UniProtKB name for the protein, or Entry Name (e.g., MOTSC_HUMAN)
3. Names of the protein
4. Gene Names - HGNC IDs of the genes that encode the proteins
5. Gene Ontology (GO) annotations

It is possible to obtain information for multiple species.
1. For HuBMAP, the organism of interest is Homo sapiens. 
2. Other applications such as SenNet would need data on
organisms such as mouse or rat.

The configuration file allows for the creation of a single file of UNIPROTKB information for multiple species. The resulting file will be named **UNIPROTKB_ALL.TSV**.

The script obtains HGNC IDs directly from genenames.org via 
a call to a CGI script.
