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

# UBKG logging utility
import ubkg_logging as ulog

def download_file(url: str, download_full_path: str, encoding: str,chunk_size=1024):

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

    # Passing gzip encoding will trigger automatic gzip decompression.
    if encoding !='':
        headers = {'Accept-encoding': encoding}

    response = requests.get(url, stream=True,headers=headers)

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

def extract_from_gzip(zipfilename: str, outputpath: str) -> str:

    # Extracts a file from the GZIP archive with file name zipfilename to outputpath.
    # Returns the full path to the extracted file.

    # Assumptions:
    # 1. The GZIP contains one file.
    # 2. The GZIP file is likely to have a file extension of GZ.
    # 3. The GZIP file is binary.
    # 4. The file is UTF-8 encoded.

    #Decompress
    with open(zipfilename,'rb') as fzip:
        file_content = gzip.decompress(fzip.read()).decode('utf-8')

    # Write output to a file with the same name as the Zip, minus the GZ file extension, if applicable.
    extract_filename = zipfilename[zipfilename.rfind('/') + 1:]
    extract_extension = extract_filename[extract_filename.rfind('.'):len(extract_filename)]
    if extract_extension.lower() == '.gz':
        extract_filename = extract_filename[0:extract_filename.rfind(extract_extension)]

    extract_path = os.path.join(outputpath, extract_filename)
    ulog.print_and_logger_info(f'Writing to {extract_path}')
    with open(extract_path, 'w') as fout:
        fout.write(file_content)

    return extract_path

def get_gzipped_file(gzip_url: str, zip_path: str, extract_path: str) -> str:

    # Downloads a GZIP archive to the specified folder and extracts the contents to the specified path.
    # Returns the full path to the extracted file.

    # Arguments:
    # gzip_url - full URL to file
    # zip_path - path of directory to which to download the ZIP file
    # extract_path - path of directory for file to be extracted from GZIP.

    # Assumptions:
    # 1. The GZIP contains one file.
    # 2. The file is UTF-8 encoded.

    # The URL contains the filename.
    zip_filename = gzip_url.split('/')[-1]
    zip_full_path = os.path.join(zip_path, zip_filename)

    # Download GZIP file.
    download_file(url=gzip_url,download_full_path=zip_full_path,encoding='gzip',chunk_size=1024)

    # Extract compressed content.
    return extract_from_gzip(zipfilename=zip_full_path,outputpath=extract_path)

def to_csv_with_progress_bar(df: pd.DataFrame, path:str):

    # Wraps the pandas to_csv with a tqdm progress bar.

    # df: DataFrame to write to CSV.
    # path: full path to CSV file.

    chunks = np.array_split(df.index, 100)  # split into 100 chunks
    for chunk, subset in enumerate(tqdm(chunks,desc='Writing')):
        if chunk == 0:  # first row
            df.loc[subset].to_csv(path, mode='w', index=True)
        else:
            df.loc[subset].to_csv(path, header=None, mode='a', index=True)

    return

def read_csv_with_progress_bar(path:str, rows_to_read: int=0,comment: str='',sep: str=',') ->pd.DataFrame:

    # Wraps the pandas read_csv with a tqdm progress bar.

    # Arguments:
    #   path: full path to CSV file.
    #   nrows: number of rows to read. The default value of 0 results in a read of all rows
    #   comment: comment character
    #   sep: separator, with default of a comma

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
        for chunk in pd.read_csv(path, chunksize=1000, comment='#', sep=sep, nrows=nrows):
            listdf.append(chunk)
            bar.update(chunk.shape[0])

    return pd.concat(listdf, axis=0, ignore_index=True)