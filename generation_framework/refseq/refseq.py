#!/usr/bin/env python

# RefSeq Gene Summary Extraction

# This script obtains the summary description for genes stored in NCBI Gene. The script:
# 1. Uses the NCBI eUtils REST API to obtain RefSeq summaries for genes, based on Entrez ID:
#    a. Calls eSearch to obtain subsets of Entrez UIDs, with a subset size (chunk) of 5000.
#    b. Calls eSummary for subsets of UIDs.
# 2. Prepares CSV files formatted to match the DEFs.csv and DEFrel.csv files of the UBKG ontology CSVs.
# 3. Appends the CSV files to DEFs.csv and DEFrel.csv.

# The summaries will be imported into the UBKG neo4j as Definition nodes linked to Entrez codes.

# Dependency:
# This script assumes that Entrez codes from GenCode data have been ingested into the UBKG CSVs.

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
import argparse


# UBKG utilities are stored in the subdirectory ..generation_framework/ukbg_utilities.

# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path.
fpath = os.path.dirname(os.getcwd())
print(f'fpath: {fpath}')
fpath = os.path.join(fpath, 'ubkg_utilities')
sys.path.append(fpath)
import ubkg_config as uconfig
import ubkg_apikey as uapikey
import ubkg_logging as ulog
import ubkg_extract as uextract

class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


def getargs() -> argparse.Namespace:

    # Parse arguments.
    parser = argparse.ArgumentParser(
    description='Extract RefSeq data for OWLNETs.\n'
                'In general you should not have the change any of the optional arguments.',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
    # positional arguments
    parser.add_argument("-s", "--skipbuild", action="store_true", help="skip build of OWLNETS files")
    args = parser.parse_args()

    return args


def getrefseqsummaries(apikey: str, outdir: str) -> pd.DataFrame:

    # Calls endpoints of the NCBI eUtils to obtain a list of summaries of all human gene Entrez IDs.

    # base URL for all calls to eUtils endpoints.
    baseurl = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'

    # Objects used to build the Pandas DataFrame returned by the function.
    listatuis = []
    listcodes = []
    listdefs = []

    # Parameters used in calls to eUtils endpoints.
    # 1. Current genes for human from the Gene database
    query = 'human[orgn]AND+alive[prop]'
    db = 'gene'
    # 2. Common parameters to control output.
    params = f'retmode=json&db={db}&apikey={apikey}'

    # Used to chunk through the gene database.
    # The eUtils API throttles responses and recommends calling eSummary with no more than 500 UIDs.

    retstart = 0
    retcount = 1
    retmax = 499

    ulog.print_and_logger_info('Obtaining RefSeq summaries for genes from NCBI eUTILs...')
    # List of UIDs to pass to call to esummary. The last list may contain fewer elements than the chunk size retmax.
    listids = []

    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

    # Chunk through Gene database.
    while retstart < retcount:

        print(f'-- range: {retstart} to {retstart + retmax}')
        # Pause to avoid a 429 error (too many requests) from eUtils.
        time.sleep(1)

        # Build esearch URL to return a chunk of Entrez UIDs to use in subsequent call to esummary.
        # The usehistory parameter results in storage of query results on the NCBI History server.
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
        retcount = int(esearchresult.get('count'))
        # List of UIDs to pass to the esummary endpoint, which has to be passed without the brackets of a Python
        # list.
        # listids = esearchresult.get('idlist')
        # argids = ','.join(listids)

        # webenv and querykey used to point to the stored search query in the history server.
        webenv = esearchresult.get('webenv')
        querykey = esearchresult.get('querykey')

        # Build summary url that returns information for the list of IDs obtained from the esearch call.
        #esummary = f'esummary.fcgi?&{params}&id={argids}'
        esummary = f'esummary.fcgi?&{params}&WebEnv={webenv}&query_key={querykey}&retstart={retstart}&retmax={retmax}'

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
            summary = gene.get('summary')

            # When a code has a definition, the UBKG generation script adds this definition with rows in the
            # DEFs.csv and DEFrel.csv files. For this case, use the following identifiers:
            # 1. ATUI: base64-encoded string concatenated from the SAB, definition string, and CUI.
            # 2. CODE: string in the standard format of `ENTREZ:uid`

            # The code will be mapped to a CUI in the UBKG CSVs.

            code = f'ENTREZ:{uid}'
            atui = f'ENTREZ {summary} CUI'
            atui = base64.urlsafe_b64encode(atui.encode('UTF-8')).decode('ascii')

            listatuis.append(atui)
            listcodes.append(code)
            listdefs.append(summary)

        # Advance to next chunk.
        retstart = retstart + retmax + 1

    # Build return--dictionary, then DataFrame. Use keys that correspond to the column headers in
    # DEFs.csv and DEFrel.csv
    dictsummary = {'ATUI:ID': listatuis, 'SAB': 'REFSEQ', 'DEF': listdefs, ':END_ID': listatuis, 'CODE': listcodes}
    dfout = pd.DataFrame.from_dict(dictsummary)
    dfout = dfout.drop_duplicates()
    dfout = dfout.dropna(subset=['DEF'])
    dfout = dfout[dfout['DEF'] != '']

    # Write to output.
    os.system(f"mkdir -p {outdir}")
    fout = os.path.join(outdir,'REFSEQ.csv')
    uextract.to_csv_with_progress_bar(df=dfout, path=fout)

    return dfout

# -------------------
# MAIN

refargs = getargs()

# Read from config file.
cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'refseq/refseq.ini')
refseq_config = uconfig.ubkgConfigParser(cfgfile)

# Obtain directory that contains the UBKG ontology CSVs, including DEFs.csv and DEFrel.csv.
csv_dir = refseq_config.get_value(section='Directories', key='csv_dir')
owlnets_dir = refseq_config.get_value(section='Directories', key='owlnets_dir')

# Get the NCBI API key for use with eUtils.
eutilapikey = uapikey.getapikey()

# Obtain the file of data extracted from RefSeq.

fRefSeq = os.path.join(owlnets_dir,'REFSEQ.csv')

if refargs.skipbuild:
    # Use existing file.
    ulog.print_and_logger_info(f'Using existing file: {fRefSeq}')
    dfsummary = uextract.read_csv_with_progress_bar(path=fRefSeq)
else:
    # Generate new file
    ulog.print_and_logger_info(f'Generating new file: {fRefSeq}')
    dfsummary = getrefseqsummaries(apikey=eutilapikey, outdir=owlnets_dir)

# Read DEFs.csv.
ulog.print_and_logger_info('Loading DEFs.csv for comparison...')
DEFs = uextract.read_csv_with_progress_bar(path=os.path.join(csv_dir, 'DEFs.csv'))
# Only add new definitions.
dfNewDEFs = dfsummary[['ATUI:ID', 'SAB', 'DEF']]
dfNewDEFs = dfNewDEFs.merge(DEFs, how='left', on='ATUI:ID')
dfNewDEFs = dfNewDEFs[pd.isna(dfNewDEFs['DEF_y'])]
dfNewDEFs = dfNewDEFs[['ATUI:ID', 'SAB_x', 'DEF_x']]
dfNewDEFs.columns = ['ATUI:ID', 'SAB', 'DEF']
ulog.print_and_logger_info('Adding new definitions to DEFs.csv...')
uextract.to_csv_with_progress_bar(
    df=dfNewDEFs, path=os.path.join(csv_dir, 'DEFs.csv'), mode='a', header=False, index=False)

# Links between definitions and CUIs.
dfNewDEFRels = dfsummary[[':END_ID', 'CODE']]

# Read DEFrels.csv
ulog.print_and_logger_info('Reading DEFrel.csv...')
DEFrel = uextract.read_csv_with_progress_bar(path=os.path.join(csv_dir, 'DEFrel.csv'))

# Read CODE-CUIs.csv. This file contains the CUIS associated with the Entrez codes. The CUIs may be
# cross-references to UMLS concepts or custom CUIs.
ulog.print_and_logger_info('Reading CUI-CODEs.csv..')
CUI_CODEs = uextract.read_csv_with_progress_bar(path=os.path.join(csv_dir, 'CUI-CODEs.csv'))

# Find CUIs for the definitions.
ulog.print_and_logger_info('Finding CUIs for Entrez codes...')
dfNewDEFRels = dfNewDEFRels.merge(CUI_CODEs,how='inner',left_on='CODE',right_on=':END_ID')
dfNewDEFRels = dfNewDEFRels[[':END_ID_x',':START_ID']]
dfNewDEFRels.columns = [':END_ID',':START_ID']

# Only add new definitions.
dfNewDEFRels = dfNewDEFRels.merge(DEFrel, how='left', on=':END_ID')
dfNewDEFRels = dfNewDEFRels[pd.isna(dfNewDEFRels[':START_ID_y'])]
dfNewDEFRels = dfNewDEFRels[[':END_ID', ':START_ID_x']]
dfNewDEFRels.columns = [':END_ID', ':START_ID']
ulog.print_and_logger_info('Adding new links to DEFrel.csv...')
uextract.to_csv_with_progress_bar(
    df=dfNewDEFRels, path=os.path.join(csv_dir, 'DEFrel.csv'), mode='a', header=False, index=False)

ulog.print_and_logger_info(f'{dfNewDEFs.shape[0]} summaries added to DEFs.csv')
