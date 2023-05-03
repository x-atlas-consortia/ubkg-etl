#!/usr/bin/env python
# coding: utf-8

# Application to test the codeReplacements function.

# Assumes the presence of a file named test.csv with a single column of codes to test--e.g.,

# code
# x
# y
# etc.

import pandas as pd
import ubkg_parsetools as up

pd.set_option('display.max_colwidth',None)
# Read test values from input file
dtest = pd.read_csv('test.csv')
dtest['converted'] = up.codeReplacements(dtest['code'],'TEST')
print(dtest)