# -*- coding: utf-8 -*-
"""
Custom module logger
"""
import logging

module_name = 'moflow'
logger = logging.getLogger(module_name)
logger.addHandler(logging.NullHandler())  # best practice to not show anything


def use_basic_config(level=logging.INFO, format=logging.BASIC_FORMAT):
    """Add basic configuration and formatting to the logger

    By default, the logger should not be configured in any way. However
    users and developers may prefer to see the logger messages.
    """
    logger.level = level
    if module_name not in [_.name for _ in logger.handlers]:
        formatter = logging.Formatter(format)
        handler = logging.StreamHandler()
        handler.name = module_name
        handler.setFormatter(formatter)
        logger.addHandler(handler)
