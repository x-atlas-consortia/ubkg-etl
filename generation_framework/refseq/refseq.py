#!/usr/bin/env python

# RefSeq Gene Summary Extraction

# This script obtains the summary description for genes stored in NCBI Gene. The script:
# 1. Uses the NCBI eUtils REST API to btain summary fields for genes, based on Entrez ID.
# 2. Prepares CSV files formatted to match the DEFs.csv and DEFrel.csv files of the UBKG ontology CSVs.
# 3. Appends the CSV files to DEFs.csv and DEFrel.csv.

#    The summaries are imported into the UBKG neo4j as Definition nodes.

# Dependency:
# This script assumes that GenCode data has been ingested into the UBKG CSVs.

# Note:
# This script is independent of the generation framework--i.e., it is not executed as a subprocess by the build_csv.py
# script.

# -----

import pandas as pd
import sys
import os
import requests
import time
import base64

# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path.
fpath = os.path.dirname(os.getcwd())
print(f'fpath: {fpath}')
fpath = os.path.join(fpath, 'ubkg_utilities')
sys.path.append(fpath)
import ubkg_config as uconfig
import ubkg_apikey as uapikey

# base URL for all calls to eUtils endpoints.
EUTILS_BASE_URL: str = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'

def getapikey()->str:

    # Get an API key for NCBI from a text file in the application directory.
    # (To obtain an API key, create an account with NCBI. The API key is part of the account profile.)
    try:
        fapikey = open(os.path.join(os.getcwd(), 'apikey.txt'), 'r')
        apikey = fapikey.read()
        fapikey.close()
    except FileNotFoundError as e:
        print('Missing file: apikey.txt')
        exit(1)

    return apikey


def getrefseqsummaries(apikey: str, baseurl: str) -> pd.DataFrame:

    # Obtains a list of summaries of all human gene Entrez IDs.

    # Objects used to build the Pandas DataFrame returned by the function.
    dictdefs = {}
    listatuis = []
    listcuis = []
    listdefs = []

    # Parameters used in calls to eUtils endpoints.

    # 1. Human species from the Gene database.
    query = 'human[orgn]'
    db = 'gene'
    # 2. Common parameters to control output.
    params = f'retmode=json&db={db}&apikey={apikey}'

    # Used to chunk through the gene database.
    retstart = 0
    retcount = 1
    retmax = 10

    print('Obtaining RefSeq summaries from NCBI eUTILs...')
    # List of UIDs to pass to call to esummary. The last list may contain fewer elements than the chunk size retmax.
    listids = []

    # Chunk through Gene database.
    #while retstart < retcount:
    while retstart < 20: # use retcount

        # Pause to avoid a 429 error (too many requests) from eUtils.
        time.sleep(1)

        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

        # Build esearch URL to return a chunk of Entrez UIDs to use in subsequent call to esummary.
        esearch = f'esearch.fcgi?&{params}&usehistory=y&retmax={retmax}&retstart={retstart}&term={query}'
        urlsearch = f'{baseurl}{esearch}'

        # Call esearch to obtain list of UIDs.
        responsesearch = requests.get(urlsearch, headers=headers)
        if responsesearch.status_code != 200:
            responsesearch.raise_for_status()

        # Obtain information from response.
        responsesearchjson = responsesearch.json()
        esearchresult = responsesearchjson.get('esearchresult')
        # Total count of UIDs. This is the same for each call.
        retcount = esearchresult.get('count')
        # List of UIDs to pass to the esummary endpoint, which has to be passed without the brackets of a Python
        # list.
        listids = esearchresult.get('idlist')
        argids = ','.join(listids)

        # Build summary url that returns information for the list of IDs obtained from the esearch call.
        esummary = f'esummary.fcgi?&{params}&id={argids}'
        urlsummary = f'{baseurl}{esummary}'
        responsesummary = requests.get(urlsummary, headers=headers)

        if responsesummary.status_code != 200:
            responsesummary.raise_for_status()

        # Obtain gene summary information for the chunk of uids.
        responsesummaryjson = responsesummary.json()
        result = responsesummaryjson.get('result')
        uids = result.get('uids')

        # Add information on each summary and uid to lists.
        for uid in uids:
            gene = result.get(uid)
            summary = gene.get('summary') # the definition

            # When a code has a definition, the UBKG generation script adds this definition with rows in the
            # DEFs.csv and DEFrel.csv files. For this case, use the following identifiers:
            # 1. ATUI: base64-encoded string concatenated from the SAB, definition string, and CUI.
            # 2. CUI: string in the standard format of `SAB:uid CUI` where ENTREZ is the SAB and CUI is a constant.

            cui = f'ENTREZ:{uid} CUI'
            atui = f'ENTREZ {summary} CUI'
            atui = base64.urlsafe_b64encode(atui.encode('UTF-8')).decode('ascii')

            listatuis.append(atui)
            listcuis.append(cui)
            listdefs.append(summary)

        # Advance to next chunk.
        retstart = retstart + retmax

    # Build return--dictionary, then DataFrame. Use keys that correspond to the column headers in
    # DEFs.csv and DEFrel.csv
    dictsummary = {'ATUI:UID': listatuis,'SAB':'REFSEQ','DEF': listdefs,':END_ID': listatuis,':START_ID':listcuis}
    return pd.DataFrame.from_dict(dictsummary)


# -------------------
# MAIN

# Read from config file
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'refseq/refseq.ini')
refseq_config = uconfig.ubkgConfigParser(cfgfile)

# Obtain directory that contains the UBKG ontology CSVs, including DEFs.csv and DEFrel.csv.
csv_dir = os.path.join(os.path.dirname(os.getcwd()), refseq_config.get_value(section='Directories', key='csv_dir'))
print(csv_dir)

# Get the NCBI API key for use with eUtils.
eutilapikey = uapikey.getapikey()
print(eutilapikey)
exit(1)
# Obtain the set of RefSeq summaries for all human genes in Gene
dfsummary= getrefseqsummaries(apikey=eutilapikey, baseurl=EUTILS_BASE_URL)


print(dfsummary)

