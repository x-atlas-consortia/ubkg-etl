#!/usr/bin/env python
# coding: utf-8

# UBKG tools for extracting, expanding, and processing source files from online sources, such as GZIP archives.
# Displays progress indicators of activities.

import requests
import os
import gzip
from tqdm import tqdm
import pandas as pd
import numpy as np
import gdown
import fileinput
import sys

# For retry loop
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


# UBKG logging utility
import ubkg_logging as ulog

def download_file_from_github(share_url: str, download_full_path: str):

    # Downloads a file as a raw file from a GitHub repo.
    # Arguments:
    # share_url: the link to the raw file in GitHub.

    ulog.print_and_logger_info(f'Downloading to {download_full_path}')
    ghfile = requests.get(share_url)
    with open(download_full_path, 'wb') as output:
        output.write(ghfile.content)

    return

def download_github_directory_content(url:str, download_full_path: str):
    """
    Downloads the contents of the specified path in a GitHub repo
    :param url: url for path in GitHub
    :param download_full_path: path to which to download file
    """

    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for bad status codes
    contents = response.json()

    files = []
    for item in contents:
        if item['type'] == 'file':
            rawurl = item['download_url']
            path_with_name = f'{download_full_path}/{item["name"]}'
            download_file_from_github(share_url=rawurl, download_full_path=path_with_name)

def download_file_from_google_drive(share_url: str, download_full_path: str):

    # Downloads a file from Google Drive.
    # Arguments:
    # share_url: the shared link obtained in Google Drive by copying the "Share" link.
    ulog.print_and_logger_info(f'Downloading to {download_full_path}')
    gdown.download(share_url, output=download_full_path, fuzzy=True)
    return

def download_folder_from_google_drive(folder_url: str, download_full_path: str):

    """
    Downloads a folder from Google Drive.
    :param folder_url: URL of the Google folder
    :param download_full_path: local directory to which to download.

    """
    ulog.print_and_logger_info(f'Downloading folder {folder_url} to {download_full_path}')
    gdown.download_folder(url=folder_url, output=download_full_path)
    return

def download_file(url: str, download_full_path: str, encoding: str = 'UTF-8', contentType: str = '', chunk_size: int = 1024):

    # Downloads a file, displaying a TQDM progress bar.

    # Arguments:
    # url - URL to execute to download file.
    # download_full_path - full path for local storage of file, including file name.
    #                      (Some download URLs, such as in NCBO BioPortal, are complex, with things like API keys, so
    #                      extracting file names may not be simple.)
    # encoding: allows for various forms of encoding. This has only been validated for the following cases:
    #           1. gzip
    #           2. no encoding
    # chunk_size: used to set the resolution of the progress update.

    # This function has been tested only for the case of downloading Gzip archives. Adding the content-type
    # header functionality may work.

    # Passing gzip encoding will trigger automatic gzip decompression.
    headers = {}
    if encoding != '':
        # headers = {'Accept-encoding': encoding}
        headers['Accept-encoding'] = encoding

    """
    if contentType == 'xlsx':
        headers['content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif contentType== 'xls':
        headers['content-type'] = 'application/vnd.ms-excel'
    elif contentType == 'csv':
        headers['content-type'] = 'text/csv'
    elif contentType == 'docx':
        headers['content-type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif contentType == 'doc':
        headers['content-type'] = 'application/msword'
    elif contentType == 'pdf':
        headers['content-type'] = 'application/pdf'
    else:
        headers['content-type'] = contentType
    """

    response = requests.get(url, stream=True, headers=headers)
    if response.status_code != 200:
        response.raise_for_status()

    # Get the size of the response (downloaded file).
    total = int(response.headers.get('content-length', 0))

    # Download the file in chunks, updating the progress bar.
    ulog.print_and_logger_info(f'Downloading...')
    with open(download_full_path, 'wb') as file, tqdm(
        desc=download_full_path,
        total=total,
        unit='iB',
        unit_scale=True,
        unit_divisor=chunk_size, # 1024 updates progress for each MB downloaded
    ) as bar:
        for data in response.iter_content(chunk_size=chunk_size):
            size = file.write(data)
            bar.update(size)

    return


def extract_from_gzip(zipfilename: str, outputpath: str, outfilename: str) -> str:

    # Extracts a file from the GZIP archive with file name zipfilename to outputpath.
    # Returns the full path to the extracted file.

    # Assumptions:
    # 1. The GZIP contains one file.
    # 2. The GZIP file is likely to have a file extension of GZ.
    # 3. The GZIP file is binary.
    # 4. The file is UTF-8 encoded.

    # Decompress
    with open(zipfilename, 'rb') as fzip:
        file_content = gzip.decompress(fzip.read()).decode('utf-8')

    if outfilename == '':
        # Write output to a file with the same name as the Zip, minus the GZ file extension, if applicable.
        extract_filename = zipfilename[zipfilename.rfind('/') + 1:]
        extract_extension = extract_filename[extract_filename.rfind('.'):len(extract_filename)]
        if extract_extension.lower() == '.gz':
            extract_filename = extract_filename[0:extract_filename.rfind(extract_extension)]
    else:
        extract_filename = outfilename

    extract_path = os.path.join(outputpath, extract_filename)
    ulog.print_and_logger_info(f'Writing to {extract_path}')
    with open(extract_path, 'w') as fout:
        fout.write(file_content)

    return extract_path


def get_gzipped_file(gzip_url: str, zip_path: str, extract_path: str, zipfilename: str = 'download.gz', outfilename: str = '') -> str:

    # Downloads a GZIP archive to the specified folder and extracts the contents to the specified path.
    # Returns the full path to the extracted file.

    # Arguments:
    # gzip_url - full URL to file
    # zip_path - path of directory to which to download the ZIP file
    # extract_path - path of directory for file to be extracted from GZIP
    # zip_filename - name of the downloaded file.

    # Assumptions:
    # 1. The GZIP contains one file.
    # 2. The file is UTF-8 encoded.

    zip_full_path = os.path.join(zip_path, zipfilename)

    # Download GZIP file.
    download_file(url=gzip_url, download_full_path=zip_full_path, encoding='gzip', chunk_size=1024)

    # Extract compressed content.
    return extract_from_gzip(zipfilename=zip_full_path, outputpath=extract_path, outfilename=outfilename)


def to_csv_with_progress_bar(df: pd.DataFrame, path: str, sep: str = ',', header: bool = True, index: bool = True, mode: str = 'w'):

    # Wraps the pandas to_csv with a tqdm progress bar.

    # df: DataFrame to write to CSV.
    # path: full path to CSV file.

    chunks = np.array_split(df.index, 100)  # split into 100 chunks
    for chunk, subset in enumerate(tqdm(chunks, desc='Writing')):
        if chunk == 0:
            #First row, which may be part of an append of the contents of df to an existing file.
            df.loc[subset].to_csv(path, header=header, mode=mode, index=index, sep=sep)
        else:
            df.loc[subset].to_csv(path, header=None, mode='a', index=index, sep=sep)

    return


def read_csv_with_progress_bar(path: str, rows_to_read: int = 0, comment: str = None, sep: str = ',', on_bad_lines: str = 'skip', encoding: str = 'utf-8', index_col: int = None) -> pd.DataFrame:

    # Wraps the pandas read_csv with a tqdm progress bar.

    # Arguments:
    #   path: full path to CSV file.
    #   nrows: number of rows to read. The default value of 0 results in a read of all rows
    #   comment: comment character, with default of None
    #   sep: separator, with default of a comma
    #   on_bad_lines, encoding: same as for read_csv

    # Returns: DataFrame

    # Get the number of lines in the file.
    with open(path, 'r') as fp:
        lines = len(fp.readlines())

    # Determine number of rows to read from the CSV.
    if rows_to_read == 0:
        nrows = lines
    else:
        nrows = rows_to_read

    # Read file in chunks, updating progress bar after each chunk.
    listdf = []
    with tqdm(total=lines, desc='Reading') as bar:
        for chunk in pd.read_csv(path, skip_blank_lines=True, chunksize=1000, comment=comment, sep=sep, nrows=nrows, on_bad_lines=on_bad_lines, encoding=encoding, index_col=index_col):
            listdf.append(chunk)
            bar.update(chunk.shape[0])

    return pd.concat(listdf, axis=0, ignore_index=True)

def header_needs_update(filetest: str, new_header: list) -> bool:
    # Check whether an update to the header is needed.
    for line in fileinput.input(filetest):
        if fileinput.isfirstline():
            header = line.rstrip('\n')
            header = header.split(',')
            break
    fileinput.close()
    return not (header == new_header)

def update_columns_to_csv_header(file: str, new_columns: list, fill: bool = False):

    # August 2023 - Moved from OWLNETS-UMLS-GRAPH
    # Updates the header of an ontology CSV file, adding new column names from the list argument.
    # This allows the addition of columns for custom properties or relationships.

    ulog.print_and_logger_info(f'Setting headers for {file} to {new_columns}...')

    if not header_needs_update(filetest=file, new_header=new_columns):
        ulog.print_and_logger_info(f'Header for {file} does not need updating.')
        return

    # Set up tqdm progress bar.
    file_size = os.path.getsize(file)
    pbar = tqdm(total=file_size, unit='MB')

    rewrite = True
    for line in fileinput.input(file, inplace=True):
        # Strip the newline from the end of the current row.
        linestrip = line.rstrip('\n')

        if fileinput.isfirstline():
            # Replace the header with the columns from the argument list.
            newline = ','.join(new_columns)
        else:
            # Write the line without the newline character, but after adding blank values for new columns.
            newline = linestrip
            if fill:
                linestrip = linestrip.split(',')
                fillcols = len(new_columns) - len(linestrip)
                for fillcols in range(fillcols):
                    newline = newline + ','

        # Write the amended line to output. Duh.
        print(newline)

        # Update progress bar.
        pbar.update(sys.getsizeof(line)-sys.getsizeof('\n'))

    pbar.close()
    fileinput.close()

    return

def getresponsejson(url: str) -> str:
    """
    Obtains a response from a REST API.
    Employs a retry loop in case of timeout or other failures.

    :param url: the URL to the REST API
    :return:
    """

    # Use the HTTPAdapter's retry strategy, as described here:
    # https://oxylabs.io/blog/python-requests-retry

    # Five retries max.
    # A backoff factor of 2, which results in exponential increases in delays before each attempt.
    # Retry for scenarios such as Service Unavailable or Too Many Requests that often are returned in case
    # of an overloaded server.

    retry = Retry(
        total=6,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET']  # Explicitly state methods (for urllib3 >=1.26.0)
    )

    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount('https://', adapter)

    try:
        response = session.get(url=url, timeout=180)
        response.raise_for_status()  # Raise error for HTTP problems
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f'Error during GET request on {url}: {e}')
        exit(1)

    except ValueError as e:

        print(f'Error decoding JSON: {e}')
        exit(1)

