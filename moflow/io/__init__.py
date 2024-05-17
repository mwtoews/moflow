
from moflow._logger import logger, logging
from moflow.mf.base import MFPackage


class MFIO:
    """Generic file object."""

    _parent_class = MFPackage
    closed = None
    parent = None

    def __init__(self, parent) -> None:
        # Set up logger
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.handlers = logger.handlers
        self.log.setLevel(logger.level)
        self.closed = True
        if parent is None:
            parent = self._parent_class()
        self.parent = parent
