#!/usr/bin/env python
# coding: utf-8

# UBKG tools for extracting source files from online sources, such as GZIP archives.

import urllib
from urllib.request import Request
import requests
import os
import gzip
from tqdm import tqdm
import mmap

import ubkg_logging as ulog

def download_file(url: str, fname: str, chunk_size=1024):

    # Downloads a file, displaying a TQDM progress bar.

    # Get the size of the response (downloaded file).
    headers = {'Accept-encoding': 'gzip'}
    resp = requests.get(url, stream=True,headers=headers)
    total = int(resp.headers.get('content-length', 0))

    ulog.print_and_logger_info(f'Downloading...')
    # Download the file, updating the progress bar.
    with open(fname, 'wb') as file, tqdm(
        desc=fname,
        total=total,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=chunk_size):
            size = file.write(data)
            bar.update(size)

    return

def extract_from_gzip(zipfilename: str, outputpath: str):

    # Extracts a file from the GZIP archive with file name zipfilename to outputpath.

    # Write output to a file with the same name as the Zip, minus the file extension.
    extract_filename = zipfilename[0:zipfilename.rfind('.')]
    extract_filename = extract_filename[extract_filename.rfind('/')+1:]
    extract_path = os.path.join(outputpath,extract_filename)
    ulog.print_and_logger_info(f'Expanding to {extract_path}')

    with gzip.open(zipfilename, 'rb') as fzip:

        fileread= fzip.read()
        try:
            file_content = gzip.decompress(fileread)
        except gzip.BadGzipFile as e:
            file_content = fileread
            ulog.print_and_logger_info(f'Not a GZipped file: {zipfilename}')

        ulog.print_and_logger_info('Writing to output...')
        with open(extract_path, 'wt') as fout:
            fout.write(str(file_content, 'utf-8'))

    return

def get_gzipped_file(gzip_url: str, owl_path: str, owlnets_path: str):

    # Downloads a GZIP archive and extracts the contents to the specified path.

    # Arguments:
    # gzip_url - full URL to GZIP file
    # extract_path - path of directory for file to be extracted from GZIP.

    # Assumptions:
    # 1. The GZIP contains one file.
    # 2. The file is UTF-8 encoded.

    # The URL contains the filename.
    zip_filename = gzip_url.split('/')[-1]
    zip_path = os.path.join(owl_path, zip_filename)

    # Download GZIP file.

    download_file(url=gzip_url,fname=zip_path,chunk_size=1024)

    # Extract compressed content.
    extract_from_gzip(zipfilename=zip_path,outputpath=owlnets_path)

    return