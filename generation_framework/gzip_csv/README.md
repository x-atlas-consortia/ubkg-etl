# CSV to OWLNETS converter

Uses the CSV file for an ontology (available in a GZ archive in BioPortal to generate a set of text files that 
comply with the OWLNETS format, as described in [https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb].

## Arguments
1. URL to the GZ file in BioPortal.
2. The name for the ontology.

## API key
To obtain relationship information specific to an ontology, the script 
calls the NCBO API. The API requires an API key, which can be obtained by creating
an account with NCBO. 

Add the API key to a file named *apikey.txt* in the application directory.
This file should be ignored by gitignore.