# Unified Biomedical Knowledge Graph (UBKG)
# Operational Generation Workflow

The following describes the process for generating a new UBKG context.

# GENERAL

## Generation machine configuration

### Memory and disk space
If you generate from a laptop, you will need 
* at least 32 GB of RAM
* a fair amount of disk space (e.g., 1TB), as you will likely store multiple versions of complete sets of ontology CSVs

### Power settings for long-running imports
The import of a single SAB can require hours to complete.
* Some OWL files (e.g., CHEBI, for which the OWL file is over 700 MB) require time both to download and to process via PheKnowLator.
* Some files (e.g., those from some DCCs) are very large.

If you generate a context from a laptop, it is possible that your machine will sleep before completing a long-running import, pausing the import until you reawaken the laptop. 
To prevent unwanted pauses in generation, you can manage the power saving features of your machine. 

### Mac OS
If you use a Mac OS laptop (e.g., MacBook Pro), you can check **Prevent automatic sleeping on power adapter when the display is off** in _System Settings/Battery_. 
If you keep your laptop plugged in to wall power, you can leave the machine to complete long-running imports.

## Globus configuration
Most of the SAB source files for Data Distillery are stored in a special Globus collection. You will need 
an account with access to the collection.

1. Install Globus Connect Personal.
2. Create a directory path on your machine.
3. Transfer source files from the Globus connection to the directory on your machine.

## Maintain ontologies.json
The **ontologies.json** configuration file indicates how each SAB is ingested. If a SAB's configuration
changes (e.g., file location), update the corresponding entry in **ontologies.json**.

## Maintain contexts.ini
The **contexts.ini** file shows all of the SABs that are part of a particular context. The **contexts.ini** file should be synchronized with the _Contexts_ page of the **ubkg_docs** repository.

In general, it is not practical
to generate an entire context with a single command:
1. Large contexts like the Data Distillery have so many SABs that attempting to ingest them all at once will result in an OOME.
2. Contexts usually involve a mixture of cached (with the _-s_ flag) and refreshed SAB sources.

The main use of the **contexts.ini** is to guide the manual workflow. If you modify the set of SABs in a context (e.g., add, remove, or change order), update both contexts.ini and the associated UBKG documentation.

## General instructions by source file type
Download configuration is a combination of information in the **ontologies.json** file and 
an INI file for a particular type of import.

### OWL files
Many SABs, especially in the base context, are OWL files available online.
1. The reference in **ontologies.json** should point to the source of the OWL file online. 
2. By default, the generation framework will
use the cached version of an OWL file. This may occur even without using the _-s_ flag. 

If you wish to obtain a new OWL file instead of using the cached version, delete the cached files in the SAB's directory in the _owl_ path. This is guaranteed to force a new download of the OWL file.

### GZIPped files
Some OWL files may be available archived as GZIP. 
1. The reference in **ontologies.json** should indicate the `/gzip_csv/gzip_csv_owlnets.py` script.
### Files from Globus
If the SAB files are stored in Globus, then:
1. The reference in **ontologies.json** should indicate the `./ubkg_edges_nodes/ubkg_edges_nodes.py` script.
2. The **edges_nodes.ini** file in the _ubkg_edges_nodes_ directory should point to the directory on the local machine to which you downloaded the files from Globus.

### SimpleKnowledge files
If the SAB file is a spreadsheet in SimpleKnowledge format, then:
1. The reference in **ontologies.json** should indicate the `./skowlnets/skowlnets.py` script.
2. The **skowlnets.ini** file in the _skowlnets_ directory should point to the file in the SimpleKnowledge repository.

### Special SABs
A number of SABs require their own scripts, including
* UNIPROTKB
* GENCODE
* CEDAR_ENTITY

Consult the **README.md** files in the appropriate directories.

#### HMFIELD
The HMFIELD SAB has a dependency on CEDAR_ENTITY and HUBMAP, which means that a refresh of HMFIELD requires the generation 
of an intermediate UBKG instance. Refer to the **README.md** file in the _hmfields_ directory.


### RefSeq
The RefSeq import affects only the **DEFs.csv** and **DEF_REL.csv** files, and uses a different script (**refseq.py**).
Consult the **README.md** file in the _refseq_ directory. The RefSeq import should be the last
import for the base context.

Consult the README.md files in the corresponding folders for more information.

## Track work
A complete refresh of a UBKG context will require days of work, and may involve importing 50 or more SABs, some of which will require hours to generate.
When generating a large context, such as the Data Distillery, track work progress. Note, at a minimum,
1. SAB
2. Date downloaded
3. Date completed

If you forget where you stopped in a refresh, open the CODES.csv file in your working directory and scroll to the bottom. Because context generation is an additive process, the last records in CODES.csv will belong to the last SAB ingested. 

## Maintain UBKGSOURCE SimpleKnowledge 
The UBKGSOURCE ontology is the source of version information for the UBKG.
UBKGSOURCE is a spreadsheet in SimpleKnowledge format. The generation framework 
points to the version of the UBKGSOURCE spreadsheet that is in the SimpleKnowledge 
repository; however, there is also a version on Google Sheets.

While refreshing a UBKG context, update the Google Sheet version of the UBKGSOURCE SimpleKnowledge sheet as you go.

When all SABs have been updated,
1. Download the Google Sheet as an Excel file.
2. Push the Excel file to the SimpleKnowledge repository.
3. Run `./build_csv.sh UBKGSOURCE` to import the version information into your context.

# PREPARATION FOR GENERATION

## Set up generation folder structure
The **.gitignore** for this repository ignores everything in the _neo4j/import_ path. This path is where
you can store the sets of CSV files that you generate.

The path should contain, at a minimum, the following types of directories:

| Name    | Role                  | Comment                                 |
|---------|-----------------------|-----------------------------------------|
| current | working directory     |                                         |
| UMLS    | UMLS CSVs from Neptue |                                         |
|base set|base context CSVs| per UMLS release--e.g., base set 2024AB |


# Build UBKG Base Context

The UMLS [releases](https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/index.html) two updates a year, in May and November.

You should generate a new base context at least after every new UMLS release. 
You may also want to generate a new base context to account for a significant update in one of the SABs of the context--e.g., Cell Ontology.

## Obtain UMLS CSVs

Once a UMLS release is available, follow the instructions in the **UBKG Source Framework** to obtain a set of **UMLS CSVs**.
Expand the Zip of UMLS CSVs to folder in your generation folder path.

## Reformat UMLS CSVs
1. Copy the UMLS CSVs into the _current_ directory.
2. Reformat the UMLS CSVs for ingestion into the UBKG by running `./build_csv.sh UMLS`. 
(See the **README.md** file in the _umls_init_ directory of this repository.)
3. Copy the CSVs in the _current_ directory to a UMLS directory.

You now have versions of both the "raw" and reformatted UMLS CSVs, in case you need to restart the generation process.

Update the UBKGSOURCE source file with details of the UMLS release.

## Import base context SABs
Using either **contexts.ini** or the _Contexts_ page of the **ubkg_docs** repository, import SABs of the base context.
Follow the specified order of ingestion--i.e., UBERON, then PATO, etc.

For each SAB in the base context, 
1. Prepare the import per the **General instructions by source file type** above.
3. Run `./build_csv.sh ` for the SAB. If you do not want a new download of source data, use the _-s_ flag.
4. Update UBKGSOURCE.

After importing all of the SABs of the base context, copy the CSVs in the _current_ directory 
to a directory named _base set <release>_--e.g., base set 2024AB. 

## Import application context SABs
If you are only updating application context SABs, then copy your base context CSVs into the _current_ directory.

Application context imports usually combine new and cached source files.
For example, for the HuBMAP/SenNet context, usually the only source files that need to be refreshed are the ones for the HUBMAP and SENNET SABs.

For each SAB in the application context,
1. Determine whether a new or cached version of source is required.
2. Prepare the import per the **General instructions by source file type** above.
3. Run `./build_csv.sh ` for the SAB. If you do not want a new download of source data, use the _-s_ flag.
4. Update UBKGSOURCE.

