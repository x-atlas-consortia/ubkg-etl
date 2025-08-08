# Unified Biomedical Knowledge Graph 

## CSV column checker

This script reformats a specified CSV so that all rows have the same number of columns.

The use case for the script is the repair of the CODEs.csv ontology file.

## Usage
python3 csv_column_checker.py -u _path_ --fix --output=_output file_

## arguments
- -u: path to the ontology CSVs. The default is **../../neo4j/import/current**.
- --fix: whether to write corrected rows to output. The default is **True**.
- input_file: name of the file to check--e.g., CODEs.csv.
- --output: name of the corrected CSV. The default is **fixed.csv**.


