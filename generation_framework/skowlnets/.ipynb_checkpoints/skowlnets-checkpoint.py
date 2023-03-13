#!/usr/bin/env python
# coding: utf-8

# # SimpleKnowledge to OWLNETS converter
# 
# Uses the input spreadsheet for the SimpleKnowledge Editor to generate a set of text files that comply with the OWLNETS format, as described in https://github.com/callahantiff/PheKnowLator/blob/master/notebooks/OWLNETS_Example_Application.ipynb.
# 
# User guide to build the SimpleKnowledge Editor spreadsheet: https://docs.google.com/document/d/1wjsOzJYRV2FRehX7NQI74ZKRXvH45l0QmClBBF_VypM/edit?usp=sharing

# In[36]:


#!/usr/bin/env python
# coding: utf-8

#SimpleKnowledge to OWLNETS converter

#Uses the input spreadsheet for the SimpleKnowledge Editor to generate text files that comply with the OWLNETS format.

#TO DO: parameterize input file name.

SIMPLEKNOWLEDGE_FILE: str = './SimpleKnowledgeHuBMAP.xlsx'

import sys
import pandas as pd
import numpy as np
import os


# In[67]:


#Read input spreadsheet.

df_sk = pd.read_excel(SIMPLEKNOWLEDGE_FILE,sheet_name='SimpleKnowledgeEditor')

#Build OWLNETS text files.


#EDGE (subject-predicate-object) DATA

#subject <tab> predicate <tab> object
#subject: code in HuBMAP ontology
#predicate: URI for relation, a relation property a standard OBO ontology
#object: code in HuBMAP ontology


edge_list_filename = './OWLNETS_edgelist.txt'

with open(edge_list_filename,'w') as out:
    out.write('subject' + '\t' + 'predicate' + '\t' + 'object' + '\n')

    #Each column after E in the spreadsheet (isa, etc.) represents a type of 
    #subject-predicate_object relationship.
    #   1. Column F represents the isa relationship. 
    #   2. Columns after F represent relationships other than isa.
    
    #A relationship is represented in an OWLNETS ontology file with a URI that corresponds
    #to a relationship property in an OBO ontology, such as RO--e.g.,
    #contains (http://purl.obolibrary.org/obo/RO_0001019). 
    #   1. For Column F (isa), the relationship is set to 'subClassOf'.
    #   2. For other columns, the relationship property is stored in the column header.
    
    #Cells in relationship columns contain comma-separated lists of object nodes. 
    
    #Thus, a relationship cell, in general, represents a set of subject-predicate-object
    #relationships between the concept in the "code" cell and the concepts in the relationship
    #cell.
      
    for index, row in df_sk.iterrows():
        if index > 0: #non-header
            subject = str(row['code'])
            
            for col in range(5,len(row)):
                #Obtain relationship property URI. This is in the format
                #term (URI)
                if col == 5:
                    predicate_uri = 'isa'
                else:
                    colhead = df_sk.columns[col]
                    predicate_uri = colhead[colhead.find('(')+1:colhead.find(')')]

                #Obtain codes in the proposed ontology for object concepts involved
                #in subject-predicate-object relationships.
                objects = row.iloc[col]
                
                if not pd.isna(objects):
                    
                    listobjects = objects.split(',')
                    
                    for obj in listobjects:
                        #Match object terms with theire respective codes (Column A), 
                        #which will result in a dataframe of one row.
                        objcode = df_sk[df_sk['term']==obj].iloc[0,1]
                        out.write(subject + '\t' + predicate_uri + '\t' + objcode + '\n')
    
     
#NODE METADATA
#Write a row for each unique concept in in the 'code' column.

node_metadata_filename = './OWLNETS_node_metadata.txt'
with open(node_metadata_filename,'w') as out:
    out.write('node_id' + '\t' + 'node_namespace' + '\t' + 'node_label' + '\t' + 'node_definition' + '\t' + 'node_synonyms' + '\t' + 'node_dbxrefs' + '\n')

    for index, row in df_sk.iterrows():
        if index > 0: #non-header
            node_id = str(row['code'])
            node_namespace = 'HubMAP'
            node_label = row['term']
            node_definition = str(row['definition'])
            node_synonyms = str(row['synonyms'])
            if not pd.isna(node_synonyms):
                node_synonyms = ''
            node_dbxrefs = str(row['dbxrefs'])
            if not pd.isna(node_dbxrefs):
                node_dbxrefs = ''
                
            out.write(node_id + '\t' + node_namespace + '\t' + node_label + '\t' + node_definition + '\t' + node_synonyms + '\t' + node_dbxrefs + '\n')

            
#RELATION METADATA
#Create a row for each type of relationship.
#Relationship URIs are defined in the headers of columns that occur after F in the 
#spreadsheet.

relation_filename = './OWLNETS_relations.txt'
with open(relation_filename,'w') as out:
    out.write('relation_id' + '\t' + 'relation_namespace' + '\t' + 'relation_label' + '\t' + 'relation_definition' + '\n')
    
    for col in range(6,len(df_sk.columns)):
        colhead = df_sk.columns[col]
        predicate_uri = colhead[colhead.find('(')+1:colhead.find(')')]
        label = colhead[0:colhead.find('(')]
        #Parse the namespace, which depends on the ontology URI.
        if predicate_uri.find('ccf') > 0:
            relation_namespace = 'CCF'
        else:
            relation_namespace = predicate_uri.split('/')[-1]
            relation_namespace = relation_namespace.replace('#','_')
            relation_namespace = relation_namespace.split('_')[0].upper()
        relation_definition = ''
        
        out.write(predicate_uri + '\t' + relation_namespace + '\t' + label + '\t' + relation_definition + '\n')


# In[ ]:




