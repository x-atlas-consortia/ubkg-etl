#!/usr/bin/env python
# coding: utf-8

# Code for obtaining api keys from text files.
import os
import ubkg_logging as ulog

def getapikey()->str:

    # Get an API key from a text file in the application directory.
    try:
        fapikey = open(os.path.join(os.getcwd(), 'apikey.txt'), 'r')
        apikey = fapikey.read()
        fapikey.close()
    except FileNotFoundError as e:
        ulog.print_and_logger_info('Missing file: apikey.txt')
        exit(1)

    return apikey