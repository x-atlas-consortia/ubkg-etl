#!/usr/bin/env python
# coding: utf-8

# UBKG QC reporting

# This class is used with files in the one of the UBKG formats--i.e.,
# 1. UBKG edges/nodes
# 2. OWLNETS

# QC reporting works with files at different points in the workflow:
# 1. After reading of edge and node files and translation of nodes and relationships.
# 2. After expansion of node dbxrefs.
# 3. After all updates to ontology CSVs are complete.


import datetime
import pandas as pd
import numpy as np


class UbkgReport:

    def __init__(self, path: str, sab: str):

        # Open a new instance of the QA report.
        self.path = path
        self.file = open(path, 'w')

        # Header
        self.write_line('UBKG INGESTION REPORT')
        self.write_bar()
        self.write_line(f'RUN DATE: {datetime.datetime.now()}')
        self.write_line(f'SAB: {sab}')
        self.write_bar()
        self.write_line('')

        # Initialize DataFrames.
        self.node_metadata = pd.DataFrame()
        self.edgelist = pd.DataFrame()
        self.explode_dbxrefs = pd.DataFrame()
        self.CODEs = pd.DataFrame()

    def report_file_statistics(self):

        # Workflow Point 1
        # Report on counts of rows in node files
        self.write_line('')
        self.write_line('FILE STATISTICS')
        self.write_bar()
        self.write_line('Numbers of non-empty rows')
        self.write_line('')
        self.write_line('Rows\tFile')
        self.write_line('----\t----')
        self.write_line(str(self.edgelist.shape[0]) + '\tEdge')
        self.write_line(str(self.node_metadata.shape[0])+ '\tNode')
        self.write_line('')

    def report_edge_node_statistics(self):

        # Workflow Point 1
        # Report on statistics related to nodes in the edges file.

        # Assumption: the edge file has been processed:
        # 1. Nodes have been parsed for SAB and code.
        # 2. Relationships have been parsed.

        self.write_line('EDGE FILE STATISTICS')
        self.write_bar()

        if len(self.edgelist) == 0:
            # Empty edge file

            self.write_line('No edge file.')
            return

        if len(self.node_metadata) == 0:
            # Empty node file
            self.write_line('No node file.')
            return

        # Counts of edge nodes by SAB
        self.count_nodes_by_sab(node_type='subject')
        self.count_nodes_by_sab(node_type='object')

        # Counts of edge nodes by whether in nodes file
        self.write_bar()
        self.write_line('')
        self.write_line('Comparison of nodes in edge file with nodes in node file')
        self.write_line('')
        self.write_node_compare_node(node_type='subject')
        self.write_node_compare_node(node_type='object')
        # Statistics on predicates
        self.write_predicate_statistics()

        return

    def write_predicate_statistics(self):

        # Workflow Point 1
        # Statistics on predicates.

        # Counts of predicates by type.

        self.write_line('')
        self.write_bar()
        self.write_line('PREDICATE STATISTICS')
        self.write_line('')
        self.write_line('Predicates without IRIs from the Relations Ontology are treated as custom labels, with inverse '
                        'relationships in the form of inverse_(label).')
        self.write_line('')

        dfbypred = self.edgelist
        dfbypred['predicate_with_label'] = dfbypred['predicate'] + '\t' + dfbypred['relation_label']
        dfbypred = self.edgelist.groupby('predicate_with_label', group_keys=False).size().sort_values(ascending=False).\
            reset_index(name='counts')
        self.write_line('Count\tPredicate')
        self.write_line('-----\t------------')

        for index, row in dfbypred.iterrows():
            self.write_line(str(row['counts']) + '\t' + row['predicate_with_label'])

        return

    def count_nodes_by_sab(self, node_type: str):

        # Return counts of nodes by SAB.
        # node_type: subject or object

        dfbysab = self.edgelist.drop_duplicates(subset=[node_type]).reset_index(drop=True)
        # JULY 2023 - Format is now SAB:CODE
        # Parsed nodes are in format SAB:code
        dfbysab['sab'] = dfbysab[node_type].str.split(':').str[0]
        dfbysab = dfbysab.groupby('sab', group_keys=False).size().sort_values(ascending=False)\
            .reset_index(name='counts')

        self.write_line('')
        self.write_line(f'Counts of unique {node_type} nodes by SAB')
        self.write_line('')
        self.write_line('Count\tSAB')
        self.write_line('-----\t---')

        for index, row in dfbysab.iterrows():
            self.write_line(str(row['counts']) + '\t' + row['sab'])

        return

        self.write_line('-----\t---')
        self.write_line('total\t'+str(dfbysab.shape[0]))

    def write_line(self, line: str):
        # Writes a line to the report file.
        line = '\n'+line
        self.file.write(line)
        return

    def write_bar(self):
        # Writes a consistent horizontal bar to the report file.
        self.write_line('--------------------')
        return

    def write_node_compare_node(self, node_type: str):

        # Returns counts of edge nodes by whether they are also in the nodes file.
        # node_type: subject or object

        self.write_line('')

        # Unique edge nodes and whether they have matching rows in the node file.
        dfedgenode = self.edgelist.drop_duplicates(subset=[node_type]).reset_index(drop=True)
        # Merge to compare.
        dfedgenode = dfedgenode.merge(self.node_metadata, how='left', left_on=node_type, right_on='node_id')
        dfedgenode['node_match'] = np.where(dfedgenode[node_type] == dfedgenode['node_id'], 'True', 'False')
        # Group by match condition.
        dfedgenodematch = dfedgenode.groupby('node_match', group_keys=False).size().sort_values(ascending=False)\
            .reset_index(name='counts')

        self.write_line(f'Counts of unique {node_type} nodes by whether they are also in node file.')
        self.write_line('(An object node that is in the edge file but not in the node file will only be '
                        'ingested if the object node is already in the ontology CSVs.)')
        self.write_line('')
        self.write_line('Count\tIn Both Edge and Node file')
        self.write_line('------\t-------')

        for index, row in dfedgenodematch.iterrows():
            self.write_line(str(row['counts']) + '\t' + row['node_match'])

        # Counts by SAB of edge nodes that are not in the nodes file.
        dfbysab = dfedgenode[dfedgenode['node_match'] == 'False']
        dfbysab = dfbysab.drop_duplicates(subset=[node_type]).reset_index(drop=True)

        # JULY 2023 Format is now SAB:CODE
        dfbysab['sab'] = dfbysab[node_type].str.split(':').str[0]
        dfbysab = dfbysab.groupby('sab', group_keys=False).size().sort_values(ascending=False).\
            reset_index(name='counts')

        if dfbysab.shape[0] > 0:
            self.write_line('')
            self.write_line(f'{node_type.capitalize()} nodes that are in the edge file but not in the node file.')

            dfmissing = dfedgenode[dfedgenode['node_match'] == 'False']

            for index, row in dfmissing.iterrows():
                self.write_line(row[node_type])

        return

    def report_dbxref_statistics(self):

        # Workflow Point 2
        # Statistics on object nodes after dbxref expansion.

        self.write_line('')
        self.write_bar()
        self.write_line('NODE STATISTICS')

        dfdbxref = self.explode_dbxrefs
        # July 2023 Format is now SAB:CODE
        dfdbxref['sab'] = dfdbxref['node_dbxrefs'].str.split(':').str[0]
        dfdbxref = dfdbxref.groupby('sab', group_keys=False).size().sort_values(ascending=False).reset_index(
            name='counts')

        self.write_bar()
        self.write_line('')
        self.write_line(f'Counts of dbxrefs by SAB')
        self.write_line('Count\tSAB')
        self.write_line('-----\t---')

        for index, row in dfdbxref.iterrows():
            self.write_line(str(row['counts']) + '\t' + row['sab'])

        return

    def report_ontology_csv_statistics(self):

        # Workflow point 3
        # Statistics on ontology CSVs.

        self.write_line('')
        self.write_bar()
        self.write_line('ONTOLOGY CSV STATISTICS')
        self.write_line('')
        self.write_line('File: CODEs.CSV')
        self.write_line('Count\tSAB')
        self.write_line('-----\t---')

        dfcodesab = self.CODEs.groupby('SAB', group_keys=False).size().sort_values(ascending=False).reset_index(
            name='counts')
        for index, row in dfcodesab.iterrows():
            self.write_line(str(row['counts']) + '\t' + row['SAB'])

        # Dbxrefs that were not established because the SABs were not in CODEs.CSV
        # The dbxrefs were provided as part of Workflow Point 2.
        # Group by SAB and compare with SABs from CODEs.csv.

        dfdbxref = self.explode_dbxrefs
        # July 2023 Format is now SAB:CODE
        dfdbxref['sab'] = dfdbxref['node_dbxrefs'].str.split(':').str[0]
        dfxrefsab = dfdbxref.groupby('sab', group_keys=False).size().sort_values(ascending=False). \
            reset_index(name='counts')

        # Merge to compare.
        dfxrefsab = dfxrefsab.merge(dfcodesab, how='left', left_on='sab',right_on='SAB')
        dfxrefsab = dfxrefsab.fillna(value={'SAB': ''})
        dfxrefsab['match_sab']=np.where(dfxrefsab['SAB'] == dfxrefsab['sab'],'True','False')
        # Filter to dbxrefs with SAB not in CODEs.csv.
        dfxrefsab = dfxrefsab[dfxrefsab['match_sab'] == 'False']
        # Group by SAB.
        dfxrefsab = dfxrefsab.groupby('sab', group_keys=False).size().sort_values(ascending=False).reset_index(
            name='counts')

        if dfxrefsab.shape[0] > 0:
            self.write_bar()
            self.write_line('')
            self.write_line('SABs for dbxrefs that are not in CODEs.csv. Nodes with these dbxrefs likely have custom CUIs.')
            self.write_line('')
            for index, row in dfxrefsab.iterrows():
                self.write_line(row['sab'])

        return


    def report_missing_node(self, nodetype: str, dfmissing: pd.DataFrame):

        # Reports subject or object nodes that are neither in the node file or in CUI-CODEs.csv (i.e, previously
        # ingested)

        if dfmissing.shape[0] > 0:
            self.write_line(f'{nodetype} nodes that were neither in nodes file or already in UBKG. Assertions for these nodes will not be ingested.')
            self.write_line('')
            for index, row in dfmissing.iterrows():
                self.write_line(row[nodetype])
        return