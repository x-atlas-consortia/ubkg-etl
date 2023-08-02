#!/usr/bin/env python

# RefSeq Gene Summary Extraction

# This script obtains the summary description for genes stored in NCBI Gene. The script:
# 1. Uses the NCBI eUtils REST API to btain summary fields for genes, based on Entrez ID.
# 2. Prepares a spreadsheet formatted to match the DEFs.csv and DEFrel.csv files of the UBKG ontology CSVs.
#    These files are imported into the UBKG neo4j as Definition nodes.

# This script runs out of band of the generation framework. The output files can be appended to the
# DEFs.csv and DEFrel.csv files.

# -----

import pandas as pd
import sys
import os
import requests
import time
import base64

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

    # Parameters used in calls.
    # 1. Human species from the Gene database.
    query = 'human[orgn]'
    db = 'gene'
    # 2. Common parameters to control output.
    params = f'retmode=json&db={db}&apikey={apikey}'

    # Used to chunk through database.
    retstart = 0
    retcount = 1
    retmax = 10

    print('Obtaining RefSeq summaries from NCBI eUTILs...')
    # List of UIDs to pass to call to esummary
    listids = []
    # List of UIDs returned from esummary
    listuids = []
    # List of UIDs, base64-encoded
    listbase64uids = []
    # List of a summaries
    listsummaries = []

    # Dictionary used to build the Pandas DataFrame.
    dictsummary = {}

    # Chunk through Gene database.
    #while retstart < retcount:
    while retstart < 20: # use retcount

        # Pause to avoid a 429 error (too many requests).
        time.sleep(1)

        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

        # Build esearch URL to return chunks of Entrez UIDs to use in subsequent call to esummary.
        esearch = f'esearch.fcgi?&{params}&usehistory=y&retmax={retmax}&retstart={retstart}&term={query}'
        urlsearch = f'{baseurl}{esearch}'

        responsesearch = requests.get(urlsearch, headers=headers)
        if responsesearch.status_code != 200:
            responsesearch.raise_for_status()

        # Obtain information from response.
        responsesearchjson = responsesearch.json()
        esearchresult = responsesearchjson.get('esearchresult')
        # Count of UIDs.
        retcount = esearchresult.get('count')

        # List of UIDs to pass to the esummary endpoint
        listids = esearchresult.get('idlist')
        argids = ','.join(listids)

        # Build summary url
        esummary = f'esummary.fcgi?&{params}&id={argids}'
        urlsummary = f'{baseurl}{esummary}'

        responsesummary = requests.get(urlsummary, headers=headers)

        if responsesummary.status_code != 200:
            responsesummary.raise_for_status()

        # Obtain summary information from response. Add to dictionary.
        responsesummaryjson = responsesummary.json()
        result = responsesummaryjson.get('result')
        uids = result.get('uids')

        for uid in uids:
            gene = result.get(uid)
            summary = gene.get('summary')
            uid = 'ENTREZ:'+uid
            listuids.append(uid)
            listbase64uids.append([base64.urlsafe_b64encode(uid.encode('UTF-8')).decode('ascii')])
            listsummaries.append(summary)

        # Advance to next chunk.
        retstart = retstart + retmax

    dictsummary = {'UID': listuids, 'ATUI:UID': listbase64uids,'SAB':'REFSEQ','DEF': listsummaries}
    return pd.DataFrame.from_dict(dictsummary)


# -------------------
# MAIN

# Get the NCBI API key for use with eUtils.
eutilapikey = getapikey()

# Obtain the full list of human gene Entrez IDs.
dfsummary= getrefseqsummaries(apikey=eutilapikey, baseurl=EUTILS_BASE_URL)
print(dfsummary)

