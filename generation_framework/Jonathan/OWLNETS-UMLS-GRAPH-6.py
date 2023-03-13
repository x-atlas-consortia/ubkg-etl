#!/usr/bin/env python
# coding: utf-8

# # OWLNETS-UMLS-GRAPH

# ## Adds OWLNETS output files content to existing UMLS-Graph-Extracts

# ### Setup

# In[1]:


import sys
import pandas as pd
import numpy as np
import base64
import json
import os


def owlnets_path(file: str) -> str:
    return os.path.join(sys.argv[1], file)


def csv_path(file: str) -> str:
    return os.path.join(sys.argv[2], file)


# Asssignnment of SAB for all relationships in edgelist - typically use owl file name before .owl
OWL_SAB = sys.argv[3].upper()

pd.set_option('display.max_colwidth', None)


# ### Ingest OWLNETS output files

# In[2]:


node_metadata = pd.read_csv(owlnets_path("OWLNETS_node_metadata.txt"), sep='\t')


# In[3]:


relations = pd.read_csv(owlnets_path("OWLNETS_relations.txt"), sep='\t')

# handle relations with None label here
relations.loc[(relations.relation_label == 'None'),'relation_label'] = np.NaN
relations.loc[relations['relation_label'].isnull(), 'relation_label'] = relations['relation_id'].str.split('#').str[-1]


# In[4]:


edgelist = pd.read_csv(owlnets_path("OWLNETS_edgelist.txt"), sep='\t')


# #### Delete self-referential edges in edgelist - CUI self-reference also avoided (later) by unique CUIs for node_ids

# In[5]:


edgelist = edgelist[edgelist['subject'] != edgelist['object']].reset_index(drop=True)


# ### Put relation_label in edgelist, convert subClassOf to isa, convert_, CodeID

# In[6]:


edgelist = edgelist.merge(relations, how='left', left_on='predicate', right_on='relation_id')
edgelist = edgelist[['subject','relation_label','object']]
del relations
edgelist.loc[(edgelist.relation_label == 'subClassOf'),'relation_label'] = 'isa'
edgelist['relation_label'] = edgelist['relation_label'].str.replace(' ', '_')

def codeReplacements(x):
   return x.str.replace('NCIT', 'NCI', regex=False).str.replace('MESH', 'MSH', regex=False).str.replace('GO ', 'GO GO:', regex=False).str.replace('NCBITaxon', 'NCBI', regex=False).str.replace('.*UMLS.*\s', 'UMLS ', regex=True).str.replace('.*SNOMED.*\s', 'SNOMEDCT_US ', regex=True).str.replace('HP ', 'HPO HP:', regex=False).str.replace('^fma','FMA ', regex=True)

edgelist['subject'] = edgelist['subject'].str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]
edgelist['subject'] = codeReplacements(edgelist['subject'])
edgelist['object'] = edgelist['object'].str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]
edgelist['object'] = codeReplacements(edgelist['object'])


# ### Add inverse_ edges

# #### Obtain inverse relations from Relations Ontology json file - address absent part_of and has_part - into 'df'

# In[7]:


df = pd.read_json("https://raw.githubusercontent.com/oborel/obo-relations/master/ro.json")
df = pd.DataFrame(df.graphs[0]['nodes'])
df = df[list(df['meta'].apply(lambda x: json.dumps(x)).str.contains('inverse of '))]
df['inverse'] = df['meta'].apply(lambda x: str(x).split(sep='inverse of ')[1].split(sep='\'')[0])
df = df[['lbl','inverse']]
inverse_df = df.copy()
inverse_df.columns = ['inverse','lbl']
df = pd.concat([df,inverse_df], axis=0).reset_index(drop=True)
del inverse_df
df['lbl'] = df['lbl'].str.replace(' ', '_').str.split('/').str[-1]
df['inverse'] = df['inverse'].str.replace(' ', '_').str.split('/').str[-1]
if len(df[(df['inverse'] == 'part_of') | (df['lbl'] == 'part_of')]) == 0:
    df.loc[len(df.index)] = ['has_part', 'part_of']
    df.loc[len(df.index)] = ['part_of', 'has_part']


# #### Join the inverse_ relations to edge list (results in some unknowns)

# In[8]:


edgelist = edgelist.merge(df, how='left', left_on='relation_label', right_on='lbl')
edgelist.drop(columns=['lbl'], inplace=True)
del df


# #### Add unknown inverse_ edges

# In[9]:


edgelist.loc[edgelist['inverse'].isnull(), 'inverse'] = 'inverse_' + edgelist['relation_label']


# ### Clean up node_metadata

# In[10]:


# Replacements
node_metadata.loc[(node_metadata.node_synonyms == 'None'),'node_synonyms'] = np.NaN
node_metadata['node_dbxrefs'] = node_metadata['node_dbxrefs'].str.upper().str.replace(':', ' ')
node_metadata['node_dbxrefs'] = codeReplacements(node_metadata['node_dbxrefs'])
node_metadata.loc[(node_metadata.node_dbxrefs == 'NONE'),'node_dbxrefs'] = np.NaN

# CodeID
node_metadata['node_id'] = node_metadata['node_id'].str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]
node_metadata['node_id'] = codeReplacements(node_metadata['node_id'])

# Unwrap Series
node_metadata['node_synonyms'] = node_metadata['node_synonyms'].str.split('|')
node_metadata['node_dbxrefs'] = node_metadata['node_dbxrefs'].str.split('|')

# Add SAB and CODE columns
node_metadata['SAB'] = node_metadata['node_id'].str.split(' ').str[0]
node_metadata['CODE'] = node_metadata['node_id'].str.split(' ').str[-1]
del node_metadata['node_namespace']


# ### Get the UMLS CUIs for each node_id as nodeCUIs

# In[11]:


explode_dbxrefs = node_metadata.explode('node_dbxrefs')[['node_id','node_dbxrefs']]
explode_dbxrefs['nodeXrefCodes'] = explode_dbxrefs['node_dbxrefs'].str.split(' ').str[-1]

explode_dbxrefs_UMLS = explode_dbxrefs[explode_dbxrefs['node_dbxrefs'].str.contains('UMLS C') == True].groupby('node_id')['nodeXrefCodes'].apply(list).reset_index(name='nodeCUIs')
node_metadata = node_metadata.merge(explode_dbxrefs_UMLS, how='left', on='node_id')
del explode_dbxrefs_UMLS
del explode_dbxrefs['nodeXrefCodes']
# del explode_dbxrefs - not deleted here because we need it later


# ### Get the UMLS CUIs for each node_id from CUI-CODEs file as CUI_CODEs

# In[12]:


CUI_CODEs = pd.read_csv(csv_path("CUI-CODEs.csv"))


# #### A big groupby - runs a couple minutes

# In[13]:


CODE_CUIss = CUI_CODEs.groupby(':END_ID')[':START_ID'].apply(list).reset_index(name='CUI_CODEs')
node_metadata = node_metadata.merge(CODE_CUIss, how='left', left_on='node_id', right_on=':END_ID')
del CODE_CUIss
del node_metadata[':END_ID']


# ### Add column for Xref's CUIs - merge exploded_node_metadata with CUI_CODEs then group and merge with node_metadata

# In[14]:


node_xref_cui = explode_dbxrefs.merge(CUI_CODEs, how='inner', left_on='node_dbxrefs', right_on=':END_ID')
node_xref_cui = node_xref_cui.groupby('node_id')[':START_ID'].apply(list).reset_index(name='XrefCUIs')
def setfunction(x):
   return set(x)
node_xref_cui['XrefCUIs'] = list(map(setfunction, node_xref_cui['XrefCUIs']))
node_xref_cui['XrefCUIs'] = node_xref_cui['XrefCUIs'].apply(list)
node_metadata = node_metadata.merge(node_xref_cui, how='left', on='node_id')
del node_xref_cui
del explode_dbxrefs


# ### Add column for base64 CUIs

# In[15]:


def base64it(x):
   return [base64.urlsafe_b64encode(str(x).encode('UTF-8')).decode('ascii')]
node_metadata['base64cui'] = node_metadata['node_id'].apply(base64it)


# ### Add cuis list and preferred cui to complete the node "atoms" (code, label, syns, xrefs, cuis, CUI)

# In[16]:


# create correct length lists
node_metadata['cuis'] = node_metadata['base64cui']
node_metadata['CUI'] = node_metadata['base64cui']

# iterate to join list across row
for index, rows in node_metadata.iterrows():
    rows.cuis = [rows.nodeCUIs, rows.CUI_CODEs, rows.XrefCUIs, rows.base64cui]

    # remove duplicates in row.cuis - can't use set because order of items matters
    res = []
    [res.append(x) for x in rows.cuis if x not in res]
    rows.cuis = res

# remove nan and flatten
node_metadata['cuis'] = node_metadata['cuis'].apply(lambda x: [i for i in x if i == i])
node_metadata['cuis'] = node_metadata['cuis'].apply(lambda x: [i for row in x for i in row])

# iterate again (ugh) to select one CUI from cuis in order - we also ensure each node_id has a distinct CUI
# each node_id is assigned one CUI distinct from all others' CUIs to ensure no self-reference in edgelist
node_idCUIs = []
for index, rows in node_metadata.iterrows():
    addedone = False
    for x in rows.cuis:
        if (x in node_idCUIs) | (addedone == True):
            dummy = 0
        else:
            rows.CUI = x
            node_idCUIs.append(x)
            addedone = True


# ### Join CUI from node_metadata to each edgelist subject and object

# #### Assemble CUI-CUIs (no prior-existance-check required), (:START_ID, :END_ID", :TYPE, SAB)

# In[17]:


# merge subject and object with their CUIs and drop the codes and add the SAB
edgelist = edgelist.merge(node_metadata, how='left', left_on='subject', right_on='node_id')
edgelist = edgelist[['CUI','relation_label','object','inverse']]
edgelist.columns = ['CUI1','relation_label','object','inverse']

edgelist = edgelist.merge(node_metadata, how='left', left_on='object', right_on='node_id')
edgelist = edgelist[['CUI1','relation_label','CUI','inverse']]
edgelist.columns = ['CUI1','relation_label','CUI2','inverse']

edgelist['SAB'] = OWL_SAB


# ## Write out files

# ### Outer join when appropriate to original csvs and then add data for each csv

# #### Write CUI-CUIs (':START_ID', ':END_ID', ':TYPE', 'SAB') and done with edgelist

# In[18]:


# TWO WRITES commented out during development

# forward ones
edgelist.columns = [':START_ID',':TYPE',':END_ID','inverse','SAB']
edgelist[[':START_ID', ':END_ID', ':TYPE', 'SAB']].to_csv(csv_path('CUI-CUIs.csv'), mode='a', header=False, index=False)

#reverse ones
edgelist.columns = [':END_ID','relation_label',':START_ID',':TYPE','SAB']
edgelist[[':START_ID', ':END_ID', ':TYPE', 'SAB']].to_csv(csv_path('CUI-CUIs.csv'), mode='a', header=False, index=False)

# del edgelist


# #### Write CODEs (CodeID:ID,SAB,CODE)

# In[19]:


newcodes = node_metadata[['node_id','SAB','CODE','CUI_CODEs']]
newcodes = newcodes[newcodes.isnull().any(axis=1)]
newcodes = newcodes.drop(columns=['CUI_CODEs'])
newcodes = newcodes.rename({'node_id': 'CodeID:ID'}, axis=1).reset_index(drop=True)

# write/append - commented out during development
newcodes.to_csv(csv_path('CODEs.csv'), mode='a', header=False, index=False)

# del newcodes


# #### Write CUIs (CUI:ID)

# In[20]:


newCUIs = node_metadata[['cuis','CUI']]
newCUIs = newCUIs[newCUIs['cuis'].apply(lambda x: x[-1]) == newCUIs['CUI']]
newCUIs = newCUIs.drop(columns=['cuis'])
newCUIs = newCUIs.rename({'CUI': 'CUI:ID'}, axis=1).reset_index(drop=True)

# write/append - commented out during development
newCUIs.to_csv(csv_path('CUIs.csv'), mode='a', header=False, index=False)

# del newCUIs


# #### Write CUI-CODEs (:START_ID,:END_ID)

# In[21]:


newCUI_CODEs = node_metadata.explode('cuis')[['cuis','base64cui','node_id','CUI']]

# left join and then select nulls to find new ones needed
newCUI_CODEs = newCUI_CODEs.merge(CUI_CODEs, how='left', left_on=['node_id','cuis'], right_on=[':END_ID',':START_ID'])
newCUI_CODEs = newCUI_CODEs[newCUI_CODEs.isnull().any(axis=1)]
newCUI_CODEs = newCUI_CODEs.drop(columns=[':START_ID',':END_ID'])

# use where condition to mark the ones to keep
newCUI_CODEs['keep'] = np.where(((newCUI_CODEs['cuis'] == newCUI_CODEs['CUI']) | ((newCUI_CODEs['cuis'] != newCUI_CODEs['base64cui'].apply(lambda x: x[-1])))), True, False)
newCUI_CODEs = newCUI_CODEs[(newCUI_CODEs['keep'] == True)]

newCUI_CODEs = newCUI_CODEs.drop(columns=['keep','CUI','base64cui'])
newCUI_CODEs = newCUI_CODEs.rename({'cuis': ':START_ID','node_id': ':END_ID'}, axis=1).reset_index(drop=True)

# write/append - commented out during development
newCUI_CODEs.to_csv(csv_path('CUI-CODEs.csv'), mode='a', header=False, index=False)

# del newCUI_CODEs


# #### Load SUIs from csv

# In[22]:


SUIs = pd.read_csv(csv_path("SUIs.csv"))
# SUIs supposedly unique but...
# discovered 5 NaN names in SUIs.csv and dropped them - ASCII converstion on original UMLS-Graph-Extract??
SUIs = SUIs.dropna().reset_index(drop=True)


# #### Write SUIs (SUI:ID,name) part 1, from label - with existence check

# In[23]:


newSUIs = node_metadata.merge(SUIs, how='left', left_on='node_label', right_on='name')[['node_id','node_label','base64cui','CUI','SUI:ID','name']]

for index, rows in newSUIs.iterrows():
    if (rows['name'] != rows['node_label']):
        rows['SUI:ID'] = base64it(rows['node_label'])[0]

# change field names
newSUIs.columns = ['node_id','name','base64cui','CUI','SUI:ID','OLDname']

# Select for NaN in name
SUIs1out = newSUIs.loc[newSUIs['OLDname'].isnull()][['SUI:ID','name']]
SUIs1out.reset_index(drop=True, inplace=True)

# write out justnewSUIs - commented out during development
SUIs1out.to_csv(csv_path('SUIs.csv'), mode='a', header=False, index=False)

# del newSUIs
# del SUIs1out


# #### Write CUI-SUIs (:START_ID,:END_ID)

# In[24]:


newCUI_SUIs = newCUIs.merge(newSUIs, how='left', left_on='CUI:ID', right_on='CUI')
newCUI_SUIs = newCUI_SUIs[['CUI:ID','SUI:ID']]
newCUI_SUIs.columns = [':START:ID',':END_ID']

# write/append - commented out during development
newCUI_SUIs.to_csv(csv_path('CUI-SUIs.csv'), mode='a', header=False, index=False)

# del newCUI_SUIs


# #### Write CODE-SUIs (:END_ID,:START_ID,:TYPE,CUI) part 1, from label

# In[ ]:


newCODE_SUIs = newSUIs[['SUI:ID','node_id','CUI']].copy()
newCODE_SUIs.insert(2, ':TYPE', 'PT')
newCODE_SUIs.columns = [':END_ID',':START_ID',':TYPE','CUI']

# write out newCODE_SUIs - commented out during development
newCODE_SUIs.to_csv(csv_path('CODE-SUIs.csv'), mode='a', header=False, index=False)

# del newCODE_SUIs


# #### Write SUIs (SUI:ID,name) part 2, from synonyms - with existence check

# In[ ]:


# explode the synonyms, remove NaN, and join with original SUIs plus SUIs1out
explode_syns = node_metadata.explode('node_synonyms')[['node_id','node_synonyms','CUI']]
explode_syns.dropna(inplace=True)
SUIs = pd.concat([SUIs,SUIs1out], axis=0).reset_index(drop=True)
newSUIs = explode_syns.merge(SUIs, how='left', left_on='node_synonyms', right_on='name')[['node_id','node_synonyms','CUI','SUI:ID','name']]

for index, rows in newSUIs.iterrows():
    if (rows['name'] != rows['node_synonyms']):
        rows['SUI:ID'] = base64it(rows['node_synonyms'])[0]

# change field names
newSUIs.columns = ['node_id','name','CUI','SUI:ID','OLDname']

# Select for NaN in name
SUIs2out = newSUIs.loc[newSUIs['OLDname'].isnull()][['SUI:ID','name']]
SUIs2out.reset_index(drop=True, inplace=True)

# write out - commented out during development
SUIs2out.to_csv(csv_path('SUIs.csv'), mode='a', header=False, index=False)

# del newSUIs
# del SUIs2out


# #### Write CODE-SUIs (:END_ID,:START_ID,:TYPE,CUI) part 2, from synonyms

# In[ ]:


newCODE_SUIs = newSUIs[['SUI:ID','node_id','CUI']].copy()
newCODE_SUIs.insert(2, ':TYPE', 'SY')
newCODE_SUIs.columns = [':END_ID',':START_ID',':TYPE','CUI']

# write out newCODE_SUIs - commented out during development
newCODE_SUIs.to_csv(csv_path('CODE-SUIs.csv'), mode='a', header=False, index=False)

# del newCODE_SUIs


# ### Backlog items:
# #### Definitions not yet available and needed from OWLNETS
# #### CUI-Semantics is a post-neo4j-build activity - needs some refinement
