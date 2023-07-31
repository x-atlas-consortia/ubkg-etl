#!/usr/bin/env python
# coding: utf-8

# UBKG functions for working with configuration files.

from configparser import ConfigParser,ExtendedInterpolation
import configparser
import os

import ubkg_logging as ulog

class ubkgConfigParser:
    def __init__(self, path: str, case_sensitive: bool = False):
        # Reads and validates the configuration file.

        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        if case_sensitive:
            # Force case sensitivity.
            self.config.optionxform = str


        if not os.path.exists(path):
            print(f'Missing configuration file: {path}')
            exit(1)
        try:
            self.config.read(path)
        except configparser.ParsingError as e:
            ulog.print_and_logger_info(f'Error parsing config file {path}')
            exit(1)

        ulog.print_and_logger_info(f'Config file found at {path}')

    def get_value(self,section: str, key:str)-> str:

        # Searches a configuration file for the value that corresponds to [section][key].
        try:
            return self.config[section][key]
        except KeyError as e:
            ulog.print_and_logger_info(f'Error reading configuration file: Missing key [{key}] in section [{section}]')
            exit(1)

    def get_section(self, section: str)-> dict:

        # Returns a section of the config file as a dictionary.

        dictreturn = {}

        try:
            sect = self.config[section]
            for key in sect:
                dictreturn[key]=self.config[section][key]
        except configparser.NoSectionError as e:
            ulog.print_and_logger_info(f'Error reading configuration file: Missing section [{section}]')
            exit(1)

        return dictreturn