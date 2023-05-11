# CSV to OWLNETS converter

Uses an ontology file in CSV format (available in a GZ archive in BioPortal) to generate a set of text files that 
comply with the OWLNETS format, as described [here](https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb).

# Content
- **gzip_csv_owlnets.py**: script that:
  - downloads from NCBO BioPortal an OWL file in CSV format, zipped as GZip.
  - extracts the CSV from the GZip.
  - translates the CSV data into a set of files in OWLNETS format.
- **apikey.txt.example**: example of an apikey.txt file.

# Arguments
1. URL to the GZ file in BioPortal.
2. The name for the ontology.

# Dependencies
1. A file named apikey.txt that contains a valid api key for calls to the NCBO BioPortal API.

# API key
To obtain relationship information specific to an ontology, the script 
calls the NCBO API. The API requires an API key, which can be obtained by creating
an account with NCBO. 

Add the API key to a file named *apikey.txt* in the application directory.
This file should be ignored by gitignore.

# To run
1. Create a file named **apikey.txt** containing a valid NCBO API key.
2. Configure the **ontologies.json** file in the root of the ubkg-etl/generation_work root.
3. Call **build_csv.sh** with the SAB of the ontology.

# Caveat
This script has been tested only with the XCO ontology.