#!/usr/bin/env python
# coding: utf-8

# Code for centralized Python logging.

import glob
import logging.config

log_dir, log, log_config = 'builds/logs', 'pkt_build_log.log', glob.glob('**/logging.ini', recursive=True)
logger = logging.getLogger(__name__)
logging.config.fileConfig(log_config[0], disable_existing_loggers=False, defaults={'log_file': log_dir + '/' + log})

def print_and_logger_info(message: str) -> None:
    print(message)
    logger.info(message)