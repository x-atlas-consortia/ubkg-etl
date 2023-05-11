#!/usr/bin/env python
# coding: utf-8

# Developer utility to test the codeReplacements function.
# Arguments:
# 1. SAB
# 2. type of file: N = Node; E = edge

# code
# x
# y
# etc.

import pandas as pd
import ubkg_parsetools as up
import sys
import os

pd.set_option('display.max_colwidth',None)
# Read test values from input file
sab = sys.argv[1]
if sys.argv[2].upper=='N':
    file = 'OWLNETS_node_metadata.txt'
    col = 'node_id'
else:
    file = 'OWLNETS_edgelist.txt'
    col = 'subject'
fpath = os.path.join(os.path.dirname(os.getcwd()),'owlnets_output',sab,file)
print(os.path.dirname(os.getcwd()))
dtest = pd.read_csv(fpath,sep='\t')

dtest['converted'] = up.codeReplacements(dtest[col],sab)
dtest = dtest[[col,'converted']]
dtest.to_csv('converted.tsv')