# -*- coding: utf-8 -*-
"""
moflow: A Python package for MODFLOW and related programs
"""
__version__ = 0.0
__author__ = 'Mike Toews'
__email__ = 'mwtoews@gmail.com'

# set up a global logger
import logging
logger = logging.getLogger('moflow')
if __name__ not in [x.name for x in logger.handlers]:
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    del formatter, handler
