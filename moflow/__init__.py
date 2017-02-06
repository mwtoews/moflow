# -*- coding: utf-8 -*-
"""
moflow: A Python package for MODFLOW and related programs
"""

# set up a module logger
import logging
logger = logging.getLogger('moflow')
handler = logging.StreamHandler()
handler.name = __name__
logger.addHandler(handler)
del handler

__version__ = 0.0
__author__ = 'Mike Toews'
__email__ = 'mwtoews@gmail.com'
