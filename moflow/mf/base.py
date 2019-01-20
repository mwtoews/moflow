import os
import numpy as np


from .._logger import logger, logging
# from .dis import DIS, DISU


class MissingFile(Exception):
    pass


class MFData(object):
    pass


class MFPackage(object):
    """The inherited ___class__.__name__ is the name of the package, which
    is always upper case and may have a version number following"""

    _float_type = np.dtype('f')  # REAL
    text = None

    @property
    def _attr_name(self):
        """It is assumed Modflow properties to be the lower-case name of Ftype,
        or the class name"""
        return self.__class__.__name__.lower()

    @property
    def _default_fname(self):
        """Generate default filename"""
        if self.nam is None:
            raise AttributeError("'nam' not set to a Modflow object")
        prefix = self.nam.prefix
        if prefix is None:
            raise ValueError("'nam.prefix' is not set")
        return prefix + '.' + self._attr_name

    @property
    def nam(self):
        """Returns back-reference to nam or Modflow object"""
        return getattr(self, '_nam', None)

    @nam.setter
    def nam(self, value):
        if value is not None and value.__class__.__name__ != 'Modflow':
            raise ValueError("'nam' needs to be a Modflow object; found " +
                             str(type(value)))
        setattr(self, '_nam', value)

    @property
    def nunit(self):
        """Nunit is the Fortran unit to be used when reading from or writing
        to the file. Any legal unit number on the computer being used can
        be specified except units 96-99. Unspecified is unit 0."""
        return getattr(self, '_nunit', 0)

    @nunit.setter
    def nunit(self, value):
        if value is None:
            value = 0
        else:
            try:
                value = int(value)
            except ValueError:
                self._logger.error("nunit: %r is not an integer", value)
        if value >= 96 and value <= 99:
            self._logger.error("nunit: %r is not valid", value)
        setattr(self, '_nunit', value)

    @property
    def fname(self):
        """Fname is the name of the file, which is a character value.
        Pathnames may be specified as part of fname. However, space characters
        are not allowed in fname. Note that this variable may not be a valid
        path to a file for all operating systems, use 'fpath' for this."""
        return getattr(self, '_fname', None)

    @fname.setter
    def fname(self, value):
        if value is not None:
            if ' ' in value:
                self._logger.warn("fname: %d space characters found in %r",
                                  value.count(' '), value)
        self._fname = value

    @property
    def fpath(self):
        """A valid path to an existing file that can be read, or has been
        written. It has precidence over 'fname' for reading."""
        return getattr(self, '_fpath', None)

    @fpath.setter
    def fpath(self, value):
        if value is not None:
            try:
                assert os.path.isfile(value)
            except:
                raise MissingFile(
                    "'%s' is not a valid path to a file" % (value,))
        self._fpath = value

    @property
    def nam_option(self):
        """Returns 'option' for Name File, which can be: OLD, REPLACE, UNKNOWN
        """
        return getattr(self, '_nam_option', None)

    @nam_option.setter
    def nam_option(self, value):
        if hasattr(value, 'upper') and value.upper() != value:
            self._logger.info('nam_option: changing value from %r to %r',
                              value, value.upper())
            value = value.upper()
        expected = [None, 'OLD', 'REPLACE', 'UNKNOWN']
        if value not in expected:
            self._logger.error("nam_option: %r is not valid; expecting one of "
                               "%r", value, expected)
        self._nam_option = value

    def __init__(self, fpath=None, *args, **kwargs):
        """Package constructor"""
        # Set up logger
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.handlers = logger.handlers
        self._logger.setLevel(logger.level)
        if args:
            self._logger.warn('unused args: %r', args)
        if 'dis' in kwargs:
            self.dis = kwargs.pop('dis')
        elif 'disu' in kwargs:
            self.disu = kwargs.pop('disu')
        if fpath is not None:
            self.fpath = fpath
            self.read()
        for kw in kwargs.keys():
            if hasattr(self, kw):
                setattr(self, kw, kwargs.pop(kw))
        if kwargs:
            self._logger.warn('unused kwargs: %r', kwargs)

    def __repr__(self):
        """Returns string representation"""
        return '<' + self.__class__.__name__ + '>'

    def read(self, *args, **kwargs):
        raise NotImplementedError("'read' not implemented for " +
                                  repr(self.__class__.__name__))

    def write(self, *args, **kwargs):
        raise NotImplementedError("'write' not implemented for " +
                                  repr(self.__class__.__name__))

    def _setup_read(self):
        """Hook to set-up attributes"""
        pass


class MFPackageDIS(MFPackage):
    """Abstract class for packages that use data from either DIS or DISU"""
    _dis = None
    _disu = None

    @property
    def dis(self):
        """Reference to DIS - Discretization Package"""
        return self._dis

    @dis.setter
    def dis(self, obj):
        import dis
        if not (obj is None or isinstance(obj, dis.DIS)):
            raise TypeError('obj is not type DIS; found ' + repr(type(obj)))
        elif obj and self.disu:
            raise TypeError("reference to 'disu' established; cannot also "
                            "attach 'dis'")
        self._dis = obj
        stress_period = getattr(self, 'stress_period', None)
        if stress_period is not None:
            if obj.nper != stress_period:
                self._logger.error('stress periods from dis.nper (%s) do not '
                                   'match those established in this package '
                                   '(%s)', obj.nper, stress_period)

    @property
    def disu(self):
        """Reference to DISU - Unstructured Discretization Package"""
        return self._disu

    @disu.setter
    def disu(self, obj):
        import dis
        if not (obj is None or isinstance(obj, dis.DISU)):
            raise TypeError('obj is not type DISU; found ' + repr(type(obj)))
        elif obj and self.dis:
            raise TypeError("reference to 'dis' established; cannot also "
                            "attach 'disu'")
        self._disu = obj
        stress_period = getattr(self, 'stress_period', None)
        if stress_period is not None:
            if obj.nper != stress_period:
                self._logger.error('stress periods from disu.nper (%s) do not '
                                   'match those established in this package '
                                   '(%s)', obj.nper, stress_period)

    @property
    def nper(self):
        """Number of stress periods in the simulation"""
        return self._dis and self._dis.nper or self._disu and self._disu.nper

    def _setup_read(self):
        """Hook to set-up and check attributes"""
        MFPackage._setup_read(self)
        if self.dis is None and self.disu is None:
            raise AttributeError("'dis' or 'disu' is not set")
