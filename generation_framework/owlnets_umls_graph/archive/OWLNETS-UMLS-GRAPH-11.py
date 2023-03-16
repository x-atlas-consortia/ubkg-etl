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


# Asssignnment of SAB for CUI-CUI relationships (edgelist) - typically use file name before .owl in CAPS
OWL_SAB = sys.argv[3].upper()

pd.set_option('display.max_colwidth', None)


# ### Ingest OWLNETS output files, remove NaN and duplicate (keys) if they were to exist

# In[2]:


node_metadata = pd.read_csv(owlnets_path("OWLNETS_node_metadata.txt"), sep='\t')
node_metadata = node_metadata.replace({'None':np.nan})
node_metadata = node_metadata.dropna(subset=['node_id']).drop_duplicates(subset='node_id').reset_index(drop=True)


# In[3]:


relations = pd.read_csv(owlnets_path("OWLNETS_relations.txt"), sep='\t')
relations = relations.replace({'None':np.nan})
relations = relations.dropna(subset=['relation_id']).drop_duplicates(subset='relation_id').reset_index(drop=True)
# handle relations with no label by inserting part after # - may warrant more robust solution or a hard stop
relations.loc[relations['relation_label'].isnull(), 'relation_label'] = relations['relation_id'].str.split('#').str[-1]


# In[4]:


edgelist = pd.read_csv(owlnets_path("OWLNETS_edgelist.txt"), sep='\t')
edgelist = edgelist.replace({'None':np.nan})
edgelist = edgelist.dropna().drop_duplicates().reset_index(drop=True)


# #### Delete self-referential edges in edgelist - CUI self-reference also avoided (later) by unique CUIs for node_ids

# In[5]:


edgelist = edgelist[edgelist['subject'] != edgelist['object']].reset_index(drop=True)


# ### Define codeReplacements function - modifies known code and xref formats to CodeID format

# In[6]:


def codeReplacements(x):
   return x.str.replace('NCIT ', 'NCI ', regex=False).str.replace('MESH ', 'MSH ', regex=False).str.replace('GO ', 'GO GO:', regex=False).str.replace('NCBITaxon ', 'NCBI ', regex=False).str.replace('.*UMLS.*\s', 'UMLS ', regex=True).str.replace('.*SNOMED.*\s', 'SNOMEDCT_US ', regex=True).str.replace('HP ', 'HPO HP:', regex=False).str.replace('^fma','FMA ', regex=True)


# ### Join relation_label in edgelist, convert subClassOf to isa and space to _, CodeID formatting

# In[7]:


edgelist = edgelist.merge(relations, how='left', left_on='predicate', right_on='relation_id')
edgelist = edgelist[['subject','relation_label','object']]
del relations

edgelist.loc[(edgelist.relation_label == 'subClassOf'),'relation_label'] = 'isa'
edgelist['relation_label'] = edgelist['relation_label'].str.replace(' ', '_')

edgelist['subject'] = edgelist['subject'].str.upper().str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]
edgelist['subject'] = codeReplacements(edgelist['subject'])
edgelist['object'] = edgelist['object'].str.upper().str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]
edgelist['object'] = codeReplacements(edgelist['object'])


# ### Add inverse_ edges

# #### Obtain inverse relations from Relations Ontology json file - address absent part_of and has_part - into 'df'

# In[8]:


df = pd.read_json("https://raw.githubusercontent.com/oborel/obo-relations/master/ro.json")
#df = pd.read_json("ro.json")

df = pd.DataFrame(df.graphs[0]['nodes'])
df = df[list(df['meta'].apply(lambda x: json.dumps(x)).str.contains('inverse of '))]
df['inverse'] = df['meta'].apply(lambda x: str(x).split(sep='inverse of ')[1].split(sep='\'')[0])
df = df[['lbl','inverse']]
inverse_df = df.copy()
inverse_df.columns = ['inverse','lbl']
df = pd.concat([df,inverse_df], axis=0).dropna().drop_duplicates().reset_index(drop=True)
del inverse_df
df['lbl'] = df['lbl'].str.replace(' ', '_').str.split('/').str[-1]
df['inverse'] = df['inverse'].str.replace(' ', '_').str.split('/').str[-1]
if len(df[(df['inverse'] == 'part_of') | (df['lbl'] == 'part_of')]) == 0:
    df.loc[len(df.index)] = ['has_part', 'part_of']
    df.loc[len(df.index)] = ['part_of', 'has_part']


# #### Join the inverse_ relations to edge list (results in some unknowns)

# In[9]:


edgelist = edgelist.merge(df, how='left', left_on='relation_label', right_on='lbl').drop_duplicates().reset_index(drop=True)
edgelist.drop(columns=['lbl'], inplace=True)
del df


# #### Add unknown inverse_ edges

# In[10]:


edgelist.loc[edgelist['inverse'].isnull(), 'inverse'] = 'inverse_' + edgelist['relation_label']


# ### Clean up node_metadata

# In[11]:


# CodeID
node_metadata['node_id'] = node_metadata['node_id'].str.replace('#', ' ').str.replace('_', ' ').str.split('/').str[-1]
node_metadata['node_id'] = codeReplacements(node_metadata['node_id'])

# synonyms .loc of notna to control for owl with no syns
node_metadata.loc[node_metadata['node_synonyms'].notna(), 'node_synonyms'] = node_metadata[node_metadata['node_synonyms'].notna()]['node_synonyms'].astype('str').str.split('|')

# dbxref .loc of notna to control for owl with no dbxref
node_metadata.loc[node_metadata['node_dbxrefs'].notna(), 'node_dbxrefs'] = node_metadata[node_metadata['node_dbxrefs'].notna()]['node_dbxrefs'].astype('str').str.upper().str.replace(':', ' ')
node_metadata['node_dbxrefs'] = node_metadata['node_dbxrefs'].str.split('|')
explode_dbxrefs = node_metadata.explode('node_dbxrefs')[['node_id','node_dbxrefs']].dropna().astype(str).drop_duplicates().reset_index(drop=True)
explode_dbxrefs['node_dbxrefs'] = codeReplacements(explode_dbxrefs['node_dbxrefs'])

# Add SAB and CODE columns
node_metadata['SAB'] = node_metadata['node_id'].str.split(' ').str[0]
node_metadata['CODE'] = node_metadata['node_id'].str.split(' ').str[-1]
del node_metadata['node_namespace']
# del explode_dbxrefs - not deleted here because we need it later


# ### Get the UMLS CUIs for each node_id as nodeCUIs

# In[12]:


explode_dbxrefs['nodeXrefCodes'] = explode_dbxrefs['node_dbxrefs'].str.split(' ').str[-1]

explode_dbxrefs_UMLS = explode_dbxrefs[explode_dbxrefs['node_dbxrefs'].str.contains('UMLS C') == True].groupby('node_id', sort=False)['nodeXrefCodes'].apply(list).reset_index(name='nodeCUIs')
node_metadata = node_metadata.merge(explode_dbxrefs_UMLS, how='left', on='node_id')
del explode_dbxrefs_UMLS
del explode_dbxrefs['nodeXrefCodes']


# ### Get the UMLS CUIs for each node_id from CUI-CODEs file as CUI_CODEs

# In[13]:


CUI_CODEs = pd.read_csv(csv_path("CUI-CODEs.csv"))
CUI_CODEs = CUI_CODEs.dropna().drop_duplicates().reset_index(drop=True)


# #### A big groupby - ran a couple minutes - changed groupby to not sort the keys to speed it up

# In[14]:


CODE_CUIs = CUI_CODEs.groupby(':END_ID', sort=False)[':START_ID'].apply(list).reset_index(name='CUI_CODEs')
node_metadata = node_metadata.merge(CODE_CUIs, how='left', left_on='node_id', right_on=':END_ID')
del CODE_CUIs
del node_metadata[':END_ID']


# ### Add column for Xref's CUIs - merge exploded_node_metadata with CUI_CODEs then group, eliminate duplicates and merge with node_metadata

# In[15]:


node_xref_cui = explode_dbxrefs.merge(CUI_CODEs, how='inner', left_on='node_dbxrefs', right_on=':END_ID')
node_xref_cui = node_xref_cui.groupby('node_id', sort=False)[':START_ID'].apply(list).reset_index(name='XrefCUIs')
node_xref_cui['XrefCUIs'] = node_xref_cui['XrefCUIs'].apply(lambda x: pd.unique(x)).apply(list)
node_metadata = node_metadata.merge(node_xref_cui, how='left', on='node_id')
del node_xref_cui
del explode_dbxrefs


# ### Add column for base64 CUIs

# In[16]:


def base64it(x):
   return [base64.urlsafe_b64encode(str(x).encode('UTF-8')).decode('ascii')]
node_metadata['base64cui'] = node_metadata['node_id'].apply(base64it)


# ### Add cuis list and preferred cui to complete the node "atoms" (code, label, syns, xrefs, cuis, CUI)

# In[17]:


# create correct length lists
node_metadata['cuis'] = node_metadata['base64cui']
node_metadata['CUI'] = ''

# join list across row
node_metadata['cuis'] = node_metadata[['nodeCUIs', 'CUI_CODEs', 'XrefCUIs', 'base64cui']].values.tolist()

# remove nan, flatten, and remove duplicates - retains order of elements which is key to consistency
node_metadata['cuis'] = node_metadata['cuis'].apply(lambda x: [i for i in x if i == i])
node_metadata['cuis'] = node_metadata['cuis'].apply(lambda x: [i for row in x for i in row])
node_metadata['cuis'] = node_metadata['cuis'].apply(lambda x: pd.unique(x)).apply(list)

# iterate to select one CUI from cuis in row order - we ensure each node_id has its own distinct CUI
# each node_id is assigned one CUI distinct from all others' CUIs to ensure no self-reference in edgelist
node_idCUIs = []
nmCUI = []
for index, rows in node_metadata.iterrows():
    addedone = False
    for x in rows.cuis:
        if ((x in node_idCUIs) | (addedone == True)):
            dummy = 0
        else:
            nmCUI.append(x)
            node_idCUIs.append(x)
            addedone = True
node_metadata['CUI'] = nmCUI


# ### Join CUI from node_metadata to each edgelist subject and object

# #### Assemble CUI-CUIs

# In[18]:


# merge subject and object with their CUIs and drop the codes and add the SAB
edgelist = edgelist.merge(node_metadata, how='left', left_on='subject', right_on='node_id')
edgelist = edgelist[['CUI','relation_label','object','inverse']]
edgelist.columns = ['CUI1','relation_label','object','inverse']

edgelist = edgelist.merge(node_metadata, how='left', left_on='object', right_on='node_id')
edgelist = edgelist[['CUI1','relation_label','CUI','inverse']]
edgelist.columns = ['CUI1','relation_label','CUI2','inverse']

edgelist = edgelist.dropna().drop_duplicates().reset_index(drop=True)

edgelist['SAB'] = OWL_SAB


# ## Write out files

# ### Test existence when appropriate in original csvs and then add data for each csv

# #### Write CUI-CUIs (':START_ID', ':END_ID', ':TYPE', 'SAB') (no prior-existance-check because want them in this SAB)

# In[19]:


# TWO WRITES comment out during development

# forward ones
edgelist.columns = [':START_ID',':TYPE',':END_ID','inverse','SAB']
edgelist[[':START_ID', ':END_ID', ':TYPE', 'SAB']].to_csv(csv_path('CUI-CUIs.csv'), mode='a', header=False, index=False)

#reverse ones
edgelist.columns = [':END_ID','relation_label',':START_ID',':TYPE','SAB']
edgelist[[':START_ID', ':END_ID', ':TYPE', 'SAB']].to_csv(csv_path('CUI-CUIs.csv'), mode='a', header=False, index=False)

del edgelist


# #### Write CODEs (CodeID:ID,SAB,CODE) - with existence check against CUI-CODE.csv

# In[20]:


newCODEs = node_metadata[['node_id','SAB','CODE','CUI_CODEs']]
newCODEs = newCODEs[newCODEs['CUI_CODEs'].isnull()]
newCODEs = newCODEs.drop(columns=['CUI_CODEs'])
newCODEs = newCODEs.rename({'node_id': 'CodeID:ID'}, axis=1)

newCODEs = newCODEs.dropna().drop_duplicates().reset_index(drop=True)
# write/append - comment out during development
newCODEs.to_csv(csv_path('CODEs.csv'), mode='a', header=False, index=False)

del newCODEs


# #### Write CUIs (CUI:ID) - with existence check against CUI-CODE.csv

# In[21]:


CUIs = CUI_CODEs[[':START_ID']].dropna().drop_duplicates().reset_index(drop=True)
CUIs.columns = ['CUI:ID']

newCUIs = node_metadata[['CUI']]
newCUIs.columns = ['CUI:ID']

# Here we isolate only the rows not already matching in existing files
df = newCUIs.drop_duplicates().merge(CUIs.drop_duplicates(), on=CUIs.columns.to_list(), how='left', indicator=True)
newCUIs = df.loc[df._merge=='left_only',df.columns!='_merge']
newCUIs.reset_index(drop=True, inplace=True)

newCUIs = newCUIs.dropna().drop_duplicates().reset_index(drop=True)
# write/append - comment out during development
newCUIs.to_csv(csv_path('CUIs.csv'), mode='a', header=False, index=False)

# del newCUIs - do not delete here because we need newCUIs list later
# del CUIs


# #### Write CUI-CODEs (:START_ID,:END_ID) - with existence check against CUI-CODE.csv

# In[22]:


# The last CUI in cuis is always base64 of node_id - here we grab those only if they are the selected CUI (and all CUIs)
newCUI_CODEsCUI = node_metadata[['CUI','node_id']]
newCUI_CODEsCUI.columns = [':START_ID',':END_ID']

# Here we grab all the rest of the cuis except for last in list (excluding single-length cuis lists first)
newCUI_CODEscuis = node_metadata[['cuis','node_id']][node_metadata['cuis'].apply(len)>1]
newCUI_CODEscuis['cuis'] = newCUI_CODEscuis['cuis'].apply(lambda x: x[:-1])
newCUI_CODEscuis = newCUI_CODEscuis.explode('cuis')[['cuis','node_id']]
newCUI_CODEscuis.columns = [':START_ID',':END_ID']

newCUI_CODEs = pd.concat([newCUI_CODEsCUI,newCUI_CODEscuis], axis=0).dropna().drop_duplicates().reset_index(drop=True)

# Here we isolate only the rows not already matching in existing files
df = newCUI_CODEs.merge(CUI_CODEs, on=CUI_CODEs.columns.to_list(), how='left', indicator=True)
newCUI_CODEs = df.loc[df._merge=='left_only',df.columns!='_merge']
newCUI_CODEs = newCUI_CODEs.dropna().drop_duplicates().reset_index(drop=True)

# write/append - comment out during development
newCUI_CODEs.to_csv(csv_path('CUI-CODEs.csv'), mode='a', header=False, index=False)

del newCUI_CODEsCUI
del newCUI_CODEscuis
del df
del newCUI_CODEs


# #### Load SUIs from csv

# In[23]:


SUIs = pd.read_csv(csv_path("SUIs.csv"))
# SUIs supposedly unique but...discovered 5 NaN names in SUIs.csv and drop them here
# ?? from ASCII converstion for Oracle to Pandas conversion on original UMLS-Graph-Extracts ??
SUIs = SUIs.dropna().drop_duplicates().reset_index(drop=True)


# #### Write SUIs (SUI:ID,name) part 1, from label - with existence check

# In[24]:


newSUIs = node_metadata.merge(SUIs, how='left', left_on='node_label', right_on='name')[['node_id','node_label','CUI','SUI:ID','name']]

# for Term.name that don't join with node_label update the SUI:ID with base64 of node_label
newSUIs.loc[(newSUIs['name'] != newSUIs['node_label']), 'SUI:ID'] = newSUIs[newSUIs['name'] != newSUIs['node_label']]['node_label'].apply(base64it).str[0]

# change field names and isolate non-matched ones (don't exist in SUIs file)
newSUIs.columns = ['node_id','name','CUI','SUI:ID','OLDname']
newSUIs = newSUIs[newSUIs['OLDname'].isnull()][['node_id','name','CUI','SUI:ID']]
newSUIs = newSUIs.dropna().drop_duplicates().reset_index(drop=True)
newSUIs = newSUIs[['SUI:ID','name']]

# update the SUIs dataframe to total those that will be in SUIs.csv
SUIs = pd.concat([SUIs,newSUIs], axis=0).reset_index(drop=True)

# write out newSUIs - comment out during development
newSUIs.to_csv(csv_path('SUIs.csv'), mode='a', header=False, index=False)

# del newSUIs - not here because we use this dataframe name later


# #### Write CUI-SUIs (:START_ID,:END_ID)

# In[25]:


# get the newCUIs associated metadata (CUIs are unique in node_metadata)
newCUI_SUIs = newCUIs.merge(node_metadata, how='inner', left_on='CUI:ID', right_on='CUI')
newCUI_SUIs = newCUI_SUIs[['node_label','CUI']].dropna().drop_duplicates().reset_index(drop=True)

# get the SUIs matches
newCUI_SUIs = newCUI_SUIs.merge(SUIs, how='left', left_on='node_label', right_on='name')[['CUI','SUI:ID']].dropna().drop_duplicates().reset_index(drop=True)
newCUI_SUIs.columns = [':START:ID',':END_ID']

# write/append - comment out during development
newCUI_SUIs.to_csv(csv_path('CUI-SUIs.csv'), mode='a', header=False, index=False)

#del newCUIs
#del newCUI_SUIs


# #### Load CODE-SUIs and reduce to PT or SY

# In[26]:


CODE_SUIs = pd.read_csv(csv_path("CODE-SUIs.csv"))
CODE_SUIs = CODE_SUIs[((CODE_SUIs[':TYPE'] == 'PT') | (CODE_SUIs[':TYPE'] == 'SY'))]
CODE_SUIs = CODE_SUIs.dropna().drop_duplicates().reset_index(drop=True)


# #### Write CODE-SUIs (:END_ID,:START_ID,:TYPE,CUI) part 1, from label - with existence check

# In[27]:


# This does NOT (yet) address two different owl files asserting two different SUIs as PT with the same CUI,CodeID by choosing the first one in the build process (by comparing only three columns in the existence check) - a Code/CUI would thus have only one PT relationship (to only one SUI) so that is not guaranteed right now (its good practice in query to deduplicate anyway results - because for example even fully addressed two PT relationships could exist between a CODE and SUI if they are asserted on different CUIs) - to assert a vocabulary-specific relationship type as vocabulary-specific preferred term (an ingest parameter perhaps) one would create a PT (if it doesn't have one) and a SAB_PT - that is the solution for an SAB that wants to assert PT on someone else's Code (CCF may want this so there could be CCF_PT Terms on UBERON codes) - note that for SY later, this is not an issue because SY are expected to be multiple and so we use all four columns in the existence check there too but intend to keep that one that way.

# get the SUIs matches
newCODE_SUIs = node_metadata.merge(SUIs, how='left', left_on='node_label', right_on='name')[['SUI:ID','node_id','CUI']].dropna().drop_duplicates().reset_index(drop=True)
newCODE_SUIs.insert(2, ':TYPE', 'PT')
newCODE_SUIs.columns = [':END_ID',':START_ID',':TYPE','CUI']

# Here we isolate only the rows not already matching in existing files
df = newCODE_SUIs.drop_duplicates().merge(CODE_SUIs.drop_duplicates(), on=CODE_SUIs.columns.to_list(), how='left', indicator=True)
newCODE_SUIs = df.loc[df._merge=='left_only',df.columns!='_merge']
newCODE_SUIs.reset_index(drop=True, inplace=True)

# write out newCODE_SUIs - comment out during development
newCODE_SUIs.to_csv(csv_path('CODE-SUIs.csv'), mode='a', header=False, index=False)

# del newCODE_SUIs - will use this variable again later (though its overwrite)


# #### Write SUIs (SUI:ID,name) part 2, from synonyms - with existence check

# In[28]:


# explode and merge the synonyms
explode_syns = node_metadata.explode('node_synonyms')[['node_id','node_synonyms','CUI']].dropna().drop_duplicates().reset_index(drop=True)
newSUIs = explode_syns.merge(SUIs, how='left', left_on='node_synonyms', right_on='name')[['node_id','node_synonyms','CUI','SUI:ID','name']]

# for Term.name that don't join with node_synonyms update the SUI:ID with base64 of node_synonyms
newSUIs.loc[(newSUIs['name'] != newSUIs['node_synonyms']), 'SUI:ID'] = newSUIs[newSUIs['name'] != newSUIs['node_synonyms']]['node_synonyms'].apply(base64it).str[0]

# change field names and isolate non-matched ones (don't exist in SUIs file)
newSUIs.columns = ['node_id','name','CUI','SUI:ID','OLDname']
newSUIs = newSUIs[newSUIs['OLDname'].isnull()][['node_id','name','CUI','SUI:ID']]
newSUIs = newSUIs.dropna().drop_duplicates().reset_index(drop=True)
newSUIs = newSUIs[['SUI:ID','name']]

# update the SUIs dataframe to total those that will be in SUIs.csv
SUIs = pd.concat([SUIs,newSUIs], axis=0).reset_index(drop=True)

# write out newSUIs - comment out during development
newSUIs.to_csv(csv_path('SUIs.csv'), mode='a', header=False, index=False)

del newSUIs
# del explode_syns


# #### Write CODE-SUIs (:END_ID,:START_ID,:TYPE,CUI) part 2, from synonyms - with existence check

# In[29]:


# get the SUIs matches
newCODE_SUIs = explode_syns.merge(SUIs, how='left', left_on='node_synonyms', right_on='name')[['SUI:ID','node_id','CUI']].dropna().drop_duplicates().reset_index(drop=True)
newCODE_SUIs.insert(2, ':TYPE', 'SY')
newCODE_SUIs.columns = [':END_ID',':START_ID',':TYPE','CUI']

#Compare the new and old retaining only new
df = newCODE_SUIs.drop_duplicates().merge(CODE_SUIs.drop_duplicates(), on=CODE_SUIs.columns.to_list(), how='left', indicator=True)
newCODE_SUIs = df.loc[df._merge=='left_only',df.columns!='_merge']
newCODE_SUIs.reset_index(drop=True, inplace=True)

# write out newCODE_SUIs - comment out during development
newCODE_SUIs.to_csv(csv_path('CODE-SUIs.csv'), mode='a', header=False, index=False)

del newCODE_SUIs


# #### Write DEFs (ATUI:ID, SAB, DEF) and DEFrel (:END_ID, :START_ID) - with check for any DEFs and existence check

# In[30]:


if node_metadata['node_definition'].notna().values.any():
    DEFs = pd.read_csv(csv_path("DEFs.csv"))
    DEFrel = pd.read_csv(csv_path("DEFrel.csv")).rename(columns={':START_ID':'CUI', ':END_ID':'ATUI:ID'})
    DEF_REL = DEFs.merge(DEFrel, how='inner', on='ATUI:ID')[['SAB','DEF','CUI']].dropna().drop_duplicates().reset_index(drop=True)
    newDEF_REL = node_metadata[['SAB','node_definition','CUI']].rename(columns={'node_definition':'DEF'})

    #Compare the new and old retaining only new
    df = newDEF_REL.drop_duplicates().merge(DEF_REL.drop_duplicates(), on=DEF_REL.columns.to_list(), how='left', indicator=True)
    newDEF_REL = df.loc[df._merge=='left_only',df.columns!='_merge']
    newDEF_REL.reset_index(drop=True, inplace=True)

    # Add identifier
    newDEF_REL['ATUI:ID'] = newDEF_REL['SAB']+" "+newDEF_REL['DEF']+" "+newDEF_REL['CUI']
    newDEF_REL['ATUI:ID'] = newDEF_REL['ATUI:ID'].apply(base64it).str[0]
    newDEF_REL = newDEF_REL[['ATUI:ID','SAB','DEF','CUI']].dropna().drop_duplicates().reset_index(drop=True)

    # Write newDEFs
    newDEF_REL[['ATUI:ID','SAB','DEF']].to_csv(csv_path('DEFs.csv'), mode='a', header=False, index=False)

    # Write newDEFrel
    newDEF_REL[['ATUI:ID','CUI']].rename(columns={'ATUI:ID':':END_ID', 'CUI':':START_ID'}).to_csv(csv_path('DEFrel.csv'), mode='a', header=False, index=False)

    del DEFs
    del DEFrel
    del DEF_REL
    del newDEF_REL

