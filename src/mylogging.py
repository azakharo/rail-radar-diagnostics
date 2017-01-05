#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os


if os.environ.get('DIAGNOST_DEBUG'):
    logging.basicConfig(format='%(message)s')
else:
    logging.basicConfig(filename='diagnost.log', format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)


def log(msg):
    _logger.debug(msg)


def info(msg):
    _logger.info(msg)


def warn(msg):
    _logger.warning("WARNING: " + msg)


def err(msg):
    _logger.error("ERROR: " + msg)


def exception(msg):
    _logger.exception(msg)
