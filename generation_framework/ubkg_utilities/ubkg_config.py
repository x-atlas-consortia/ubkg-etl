#!/usr/bin/env python
# coding: utf-8

# UBKG functions for working with configuration files.

from configparser import ConfigParser,ExtendedInterpolation

class ubkgConfigParser:
    def __init__(self, path: str):
        # Reads and validates the configuration file.

        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        try:
            self.config.read(path)
        except FileNotFoundError as e:
            print(f'Missing configuration file: {path}')
            exit(1)

    def get_value(self,section: str, key:str)-> str:

        # Searches a configuration file for the value that corresponds to [section][key].
        try:
            return self.config[section][key]
        except KeyError as e:
            print(f'Missing key [{key}] in section [{section}')
            exit(1)
