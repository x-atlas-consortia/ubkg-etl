#!/usr/bin/env python
# coding: utf-8

# UBKG functions for cleaning CSV files.

import pandas as pd
import ubkg_extract as uextract
import ubkg_logging as ulog

def remove_duplicates(csvpath: str):

    # Removes duplicate rows from a CSV.

    ulog.print_and_logger_info(f'Removing duplicate rows from {csvpath}...')
    ulog.print_and_logger_info('-- Reading file...')
    dfcsv = uextract.read_csv_with_progress_bar(path=csvpath)
    rowsbefore = dfcsv.shape[0]

    dfcsv = dfcsv.drop_duplicates().reset_index(drop=True)
    rowsafter = dfcsv.shape[0]

    duplicaterows = rowsbefore - rowsafter

    if duplicaterows > 0:
        ulog.print_and_logger_info('-- Writing deduplicated file back...')
        uextract.to_csv_with_progress_bar(df=dfcsv,path=csvpath, mode='w', header=True, index=False)

    ulog.print_and_logger_info(f'-- {rowsbefore-rowsafter} duplicate rows removed.')


    return



