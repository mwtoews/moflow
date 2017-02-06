# -*- coding: utf-8 -*-

from ..mf.base import MFPackage
from .. import logger, logging


class MFIO(object):
    """Generic file object"""
    _parent_class = MFPackage
    closed = None
    parent = None

    def __init__(self, parent):
        # Set up logger
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.handlers = logger.handlers
        self.log.setLevel(logger.level)
        self.closed = True
        if parent is None:
            parent = self._parent_class()
        self.parent = parent
        return
