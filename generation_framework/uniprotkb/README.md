# UNIPROT KB to OWLNETS converter

Converts to OWLNETS format (described in [https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb])
data obtained from UniProt.org.

There are no required (positional) arguments for the script.

It is possible to obtain data from [UniProt.org](https://www.uniprot.org/uniprotkb?query=*) by executing a call to UniProt's REST API. 
For the purposes of our ontology, the relevant information is:
1. UniProtDB entry (e.g., AOA0C5B5G6)
2. UniProtKB name for the protein, or Entry Name (e.g., MOTSC_HUMAN)
3. Names of the protein
4. Gene Names - HGNC IDs of the genes that encode the proteins

For HuBMAP, the organism of interest is Homo sapiens. 
Other applications such as SenNet would need data on
organisms such as mice.

The URL to pull the relevant information for HuBMAP is:
https://rest.uniprot.org/uniprotkb/stream?compressed=true&fields=accession%2Cid%2Cprotein_name%2Cgene_names&format=tsv&query=%28%2A%29%20AND%20%28model_organism%3A9606%29

This results in a fairly large (4 GB) compressed file.

The script obtains HGNC IDs directly from genenames.org via 
a call to a CGI script.
