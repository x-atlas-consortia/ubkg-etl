# Unified Biomedical Knowledge Graph
## GenCode ingestion script

### Purpose
The scripts in this folder generate files in UBKG edges/nodes format for ingestion of data from GenCode.

### Content
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
  - uses the translated annotation data to build edges and nodes files.
- **gencode.ini.example**: annotated example of an application configuration file.

### File Dependencies
1. Files in the **ubkg_utilities** folder:
   - ubkg_extract.py
   - ubkg_logging.py
   - ubkg_config.py
2. An application configuration file named **gencode.ini.**

### Precursor Assertions
Some GenCode assertions employ nodes from other sets of assertions, including:
1. GENCODE_ONT: custom nodes, in a source file built with the SimpleKnowledge framework
2. PGO: Pseudogene Ontology

Note: In the UBKG, codeIDs for PGO nodes are in the format **PGO PGO:(code)**, similar to the formats for GO, HPO, and HGNC.

GENCODE_ONT is a special case. The GENCODE annotated file refers to nodes in GENCODE_ONT by term instead of code,
so it is necessary to map from term to code in GENCODE_ONT. The script assumes that GENCODE_ONT has been ingested so 
that the file **OWLNETS_node_metadata.txt** is available.

### To run
Copy and modify **gencode.ini.example** to a file named **gencode.ini** in the gencode directory.

# GenCode Model

Each row in the translated annotation file corresponds to a GenCode annotation.
Each annotation can correspond to a set of assertions in the UBKG.

GenCode assertions involve the following types of nodes:
1. annotation nodes (i.e., identified with Ensembl IDs; created as part of the GENCODE ingestion) 
2. nodes from the GENCODE_ONT ontology.
3. RefSeq nodes (which are created as part of the GENCODE ingestion)

## Transcript-specific Assertions

An annotation node that corresponds to a transcript can be the subject in the following types of assertions:

| predicate  IRI                            | predicate label  | column in annotation file | node type       |
|-------------------------------------------|------------------|---------------------------|-----------------|
| http://purl.obolibrary.org/obo/RO_0002510 | transcribed_from | gene_id                   | annotation node |
| http://purl.obolibrary.org/obo/RO_0002205 | has_gene_product | UNIPROTKB_SwissProt_AN    | UNIPROTKB       |
| http://purl.obolibrary.org/obo/RO_0002205 | has_gene_product | UNIPROTKB_Trembl_AN       | UNIPROTKB       |

### transcribed_in
![img.png](img.png)
### has_gene_product
![img_1.png](img_1.png)

## Feature-level Assertions

Every annotation node can be the subject of a number of assertions.
Node_ids for object nodes are from:
1. Nodes in the **OWLNETS_node_metadata.txt** file created during the ingestion of the GENCODE_ONT SAB
2. Nodes from the PsuedoGene Ontology (PGO), ingested from an OWL file.


| predicate  IRI                              | predicate label       | column in annotation file | node type   |
|---------------------------------------------|-----------------------|---------------------------|-------------|
| 'http://purl.obolibrary.org/obo/RO_0001025' | located_in            | chromosome_name           | GENCODE_ONT |
|                                             | is_feature_type       | feature_type              | GENCODE_ONT |
|                                             | is_gene_biotype       | gene_type                 | GENCODE_ONT |
|                                             | is_transcript_biotype | transcript_type           | GENCODE_ONT |
| http://purl.obolibrary.org/obo/RO_0004048   | has_directional_form  | genomic_strand            | GENCODE_ONT |
| subClassOf                                  | isa                   | ont                       | PGO         |
|                                             | has_RefSeq_ID         | RefSeq_RNA_id             | REFSEQ      |

### located_in
![img_2.png](img_2.png)
### is_feature_type
![img_3.png](img_3.png)
### is_gene_biotype
![img_4.png](img_4.png)
### is_transcript_biotype
![img_5.png](img_5.png)
### has_directional_form
![img_6.png](img_6.png)
### subClassOf (PGO)
![img_7.png](img_7.png)
### has_RefSeq_ID
![img_8.png](img_8.png)


## Node information

### Annotation nodes
Each annotation node has the following characteristics:

| fields in annotation file | characteristic                              |
|---------------------------|---------------------------------------------|
| genomic_start_location    | **lowerbound** property                     |
| genomic_end_location      | **upperbound** property                     |
| HGNC ID                   | dbxref to HGNC node                         |

![img_10.png](img_10.png)


### Entrez nodes
A node will be created for each value in the _Entrez_Gene_id_ field of the annotation file.
These nodes have dbxrefs to HGNC nodes.

![img_11.png](img_11.png)

### RefSeq nodes
A node will be created for each value in the _RefSeq_RNA_id_ or _RefSeq_protein_id_ field of the annotation file. 
RefSeq nodes will be in **has RefSeq** assertions.

