#!/usr/bin/env python
# coding: utf-8

# Code for centralized Python logging.

import glob
import logging.config
import os

# July 2023 - Reconfigured relative file paths to allow for more general use.
#log_dir, log, log_config = 'builds/logs', 'pkt_build_log.log', glob.glob('**/logging.ini', recursive=True)

fpath = os.path.dirname(os.getcwd())
if 'generation_framework' in fpath:
    builds_dir = os.path.join(fpath,'builds')
else:
    builds_dir = os.path.join(fpath,'generation_framework/builds')

log_dir = os.path.join(builds_dir,'logs')
log = 'ubkg.log'
logger = logging.getLogger(__name__)

log_config = os.path.join(builds_dir,'logging.ini')
#logging.config.fileConfig(log_config[0], disable_existing_loggers=False, defaults={'log_file': log_dir + '/' + log})
logging.config.fileConfig(log_config, disable_existing_loggers=False, defaults={'log_file': log_dir + '/' + log})

def print_and_logger_info(message: str) -> None:
    print(message)
    logger.info(message)