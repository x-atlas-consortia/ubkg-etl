# UMLS CSV CodeID Formatter

Standardizes the format of code IDs in CSVs obtained from
an extraction of UMLS data from the DBMI Neptune data warehouse.

# Background
The UMLS data in Neptune adheres closely to the original content from the UMLS--i.e., files in Rich Release Format (RRF),
such as MRCONSO.RRF.

The UBKG source framework script creates a "CodeID" property field for each code by concatenating the code's 
_Source Abbreviation_ (SAB)--the idenfifier of the code's vocabulary--and the code.
The source framework uses the space character as a delimiter.

A small number of vocabularies in the UMLS do not conform to UMLS standard that keeps codes and SABs separate.
Unfortunately, most of these vocabularies are significant for the UBKG.

The **umls_init.py** script standardizes the formatting of codes and CodeIDs for codes 
from the UMLS. Although it is possible to reformat codes at the time of extraction from
Neptune, standardizing UMLS codes before ingesting the other SABs offers benefits including:
1. We keep a copy of the codes as originally formatted in UMLS.
2. We have more control over formatting logic.

# Reformatting
The standardized formats for CODE and CodeID are:
1. The CODE does not include the SAB.
2. The CodeID format is _SAB_:_CODE_--i.e., the colon is the delimiter.

Reformatting specific to SABs:

| SAB               | Original Format            | New Format                | Description                                    |
|-------------------|----------------------------|---------------------------|------------------------------------------------|
| HGNC              | HGNC HGNC:CODE             | HGNC:CODE                 | Remove SAB from code                           |
| GO                | GO GO:CODE                 | GO:CODE                   | Remove SAB from code                           |
| HPO               | HPO HP:CODE                | HPO:CODE                  | Set SAB to HPO; remove SAB from code           |
| HCPCS Level codes | HCPCS Level n: Exxxx-Exxxx | HCPCS:Level_n_Exxxx-Exxxx | Removed colon; replaced spaces with underscore |


# Content
- **umls_init.py** - Does the following:
   - Reads a configuration file.
   - For each CSV indicated as a key in the File_Column section,
     - Reads the file.
     - Reformats each column listed in the value, based on the content of the **Duplicate_SAB** section.
     - Replaces the original file with the reformatted file.
- **umls_init.ini** - annotated INI file.

# Dependencies
Files in the **ubkg_utilities** folder:
   - ubkg_extract.py
   - ubkg_logging.py
   - ubkg_config.py