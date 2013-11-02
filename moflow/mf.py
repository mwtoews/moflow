# -*- coding: utf-8 -*-
"""
Modflow module
"""

import os
import re
import inspect
import numpy as np

from . import logger, logging


class MFReaderError(Exception):
    """MODFLOW file read error"""
    def __init__(self, fp, message, *message_params):
        """Requires MFFile obj and error message."""
        if not isinstance(fp, _MFFileReader):
            raise TypeError("'fp' is not a 'MFFile' object")
        self.fp = fp
        self.objname = self.fp.parent.__class__.__name__
        self.message = message % message_params

    def __str__(self):
        """Return error message"""
        return '%s:%s:%s:Data set %s:%s' % \
            (self.objname, self.fp.fname, self.fp.lineno,
             self.fp.data_set_num, self.message)


class _MFFileReader(object):
    """MODFLOW file reader"""

    def __init__(self, parent):
        """Initialize with parent _MFPackage. File is read from parent.fpath
        property, which is typically a path to a filename, but can also be a
        file reader object with a 'readlines' method, such as BytesIO."""
        # Set up logger
        self.logger = logging.getLogger(parent.__class__.__name__ + 'Reader')
        self.logger.handlers = logger.handlers
        self.logger.setLevel(logger.level)
        if not isinstance(parent, _MFPackage):
            raise ValueError("'parent' needs to be a _MFPackage object; found "
                             + str(type(parent)))
        self.parent = parent
        if hasattr(self.parent.fpath, 'readlines'):
            # it is a file reader object, e.g. BytesIO
            self.fname = self.parent.fpath.__class__.__name__
            self.lines = self.parent.fpath.readlines()
        else:
            self.fname = self.parent.fname
            if self.fname is None:
                self.fname = os.path.split(self.parent.fpath)[1]
            # Read whole file at once, then close it
            with open(self.parent.fpath, 'r') as fp:
                self.lines = fp.readlines()
        self.logger.info("read file '%s' with %d lines",
                         self.fname, len(self.lines))
        self.lineno = 0
        self.data_set_num = 0

    def __len__(self):
        """Returns number of lines"""
        return len(self.lines)

    @property
    def not_eof(self):
        """Reader is not at the end of file (EOF)"""
        return self.lineno < len(self.lines)

    def next_line(self, data_set_num=None):
        """Get next line and increment lineno.
        Raises MFReaderError if the next line does not exist"""
        self.data_set_num = data_set_num
        self.lineno += 1
        try:
            line = self.lines[self.lineno - 1]
        except IndexError:
            self.lineno -= 1
            raise MFReaderError(self, 'Unexpected end of file')
        if len(line) > 199:
            self.logger.warn('%d: line has %d characters',
                             self.lineno, len(line))
        return line

    def get_named_items(self, data_set_num, names, fmt='s'):
        """Get items into dict. See get_items for fmt usage"""
        items = self.get_items(data_set_num, len(names), fmt=None)
        if isinstance(fmt, str):
            fmt = [fmt] * len(names)
        res = {}
        if isinstance(fmt, list):
            assert len(fmt) == len(names), (len(fmt), len(names))
            for name, item, f in zip(names, items, fmt):
                res[name] = self.conv(item, f, name)
        elif fmt is None:
            for name, item in zip(names, items):
                res[name] = item
        else:
            raise ValueError('Unknown case for fmt=' + repr(fmt))
        return res

    def conv(self, item, fmt, name=None):
        """Helper function to convert item using a format fmt, raises
        MFReaderError showing helpful info if data could not be converted.
        The format code must be one of 'i' (integer), 'f' (any floating point),
        or 's' (string). It could also be a numpy dtype."""
        try:
            if type(fmt) == np.dtype:
                return fmt.type(item)
            elif fmt == 's':  # string
                return item
            elif fmt == 'i':  # integer
                return int(item)
            elif fmt == 'f':  # any floating-point number
                # typically either a REAL or DOUBLE PRECISION
                return self.parent._float_type.type(item)
            else:
                raise ValueError('Unknown fmt code %r' % (fmt,))
        except ValueError:
            if name is not None:
                msg = 'Cannot cast %s %r to type %r' % (name, item, fmt)
            else:
                msg = 'Cannot cast %r to type %r' % (item, fmt)
            raise MFReaderError(self, msg)

    def get_items(self, data_set_num=None, num_items=None, fmt='s'):
        """Get items from one or more lines into list. If num_items is
        defined, then only this count will be returned and any remaining
        items from the line will be ignored.
        If fmt is defined, it must be:
         - 's' for string or no conversion (default)
         - 'i' for integer
         - 'f' for float, as defined by parent._float_type
        Furthermore, it can be either one character or a list the same length
        as num_items."""
        if num_items is None:
            items = self.next_line(data_set_num).split()
        else:
            assert isinstance(num_items, int), type(num_items)
            assert num_items > 0, num_items
            items = []
            while len(items) < num_items:
                items += self.next_line(data_set_num).split()
            if len(items) > num_items:  # trim off too many
                items = items[:num_items]
        if isinstance(fmt, str):
            res = [self.conv(x, fmt) for x in items]
        elif isinstance(fmt, list):
            assert len(fmt) == num_items, (len(fmt), num_items)
            res = [self.conv(x, f) for x, f in zip(items, fmt)]
        elif fmt is None:
            res = items
        else:
            raise ValueError('Unknown case for fmt=' + repr(fmt))
        return res

    def read_named_items(self, data_set_num, names, fmt='s'):
        """Read items into parent. See get_items for fmt usage"""
        items = self.get_named_items(data_set_num, names, fmt)
        for name in items.keys():
            setattr(self.parent, name, items[name])

    def read_text(self, data_set_num=0):
        """Reads 0 or more text (comment) for lines that start with '#'"""
        self.parent.text = []
        line = self.next_line(data_set_num)
        while line.startswith('#'):
            line = line[1:].strip()
            self.parent.text.append(line)
            if not self.not_eof:
                return
            line = self.next_line(data_set_num)
        self.lineno -= 1  # scroll back one


class _MFPackage(object):
    """The inherited ___class__.__name__ is the name of the package, which
    is always upper case and my have a version number following"""

    @property
    def _attr_name(self):
        """It is assumed Modflow properties to be the lower-case name of Ftype,
        or the class name"""
        return self.__class__.__name__.lower()

    @property
    def _default_fname(self):
        """Generate default filename"""
        if self.parent is None:
            raise AttributeError("'parent' not set to a Modflow object")
        prefix = self.parent.prefix
        if prefix is None:
            raise ValueError("'parent.prefix' is not set")
        return prefix + '.' + self._attr_name

    @property
    def parent(self):
        """Returns back-reference to Modflow object"""
        return getattr(self, '_parent', None)

    @parent.setter
    def parent(self, value):
        if value is not None and not isinstance(value, Modflow):
            raise ValueError("'parent' needs to be a Modflow object; found "
                             + str(type(value)))
        setattr(self, '_parent', value)

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
        are not allowed in fname."""
        return getattr(self, '_fname', None)

    @fname.setter
    def fname(self, value):
        if value is not None:
            if ' ' in value:
                self._logger.warn("fname: %d space characters found in %r",
                                  value.count(' '), value)
            if os.path.sep == '/':  # for reading on POSIX systems
                if '\\' in value:
                    self._logger.info(r"fname: replacing '\' with '/' path "
                                      "separators to read file on host system")
                    value = value.replace('\\', '/')
        self._fname = value

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

    def read(self, *args, **kwargs):
        raise NotImplementedError("'read' not implemented for " +
                                  repr(self.__class__.__name__))

    def write(self, *args, **kwargs):
        raise NotImplementedError("'write' not implemented for " +
                                  repr(self.__class__.__name__))

    text = None
    _float_type = np.dtype('f')  # REAL

    def __init__(self):
        """Package constructor"""
        # Set up logger
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.handlers = logger.handlers
        self._logger.setLevel(logger.level)


class DIS(_MFPackage):
    """Discretization file"""


class DISU(_MFPackage):
    """Unstructured Discretization file"""


class MULT(_MFPackage):
    """Multiplier array file"""


class ZONE(_MFPackage):
    """Zone array"""


class PVAL(_MFPackage):
    """Parameter Value file"""


class BAS6(_MFPackage):
    """Ground-Water Flow Process Basic Package"""


class OC(_MFPackage):
    """Ground-Water Flow Process Output Control Option"""


class BCF6(_MFPackage):
    """Ground-Water Flow Process Block-Centered Flow Package"""


class LPF(_MFPackage):
    """Ground-Water Flow Process Layer Property Flow Package"""


class HUF2(_MFPackage):
    """Hydrogeologic Unit Flow Package"""


class UPW(_MFPackage):
    """Upstream Weighting Package (MODFLOW-NWT only)"""


class SWT(_MFPackage):
    """Subsidence and Aquifer-System Compaction Package for Water-Table
    Aquifers"""


class HFB6(_MFPackage):
    """Ground-Water Flow Process Horizontal Flow Barrier Package"""


class UZF(_MFPackage):
    """Ground-Water Flow Process Unsaturated-Zone Flow Package"""


class RCH(_MFPackage):
    """Ground-Water Flow Process Recharge Package"""


class RIV(_MFPackage):
    """Ground-Water Flow Process River Package"""


class WEL(_MFPackage):
    """Ground-Water Flow Process Well Package"""


class DRN(_MFPackage):
    """Ground-Water Flow Process Drain Package"""


class GHB(_MFPackage):
    """Ground-Water Flow Process General-Head Boundary Package"""


class EVT(_MFPackage):
    """Ground-Water Flow Process Evapotranspiration Package"""


class CHD(_MFPackage):
    """Ground-Water Flow Process Time-Variant Specified-Head Package"""


class SIP(_MFPackage):
    """Strongly Implicit Procedure Package"""


class SOR(_MFPackage):
    """Slice-Successive Over-Relaxation Package"""


class PCG(_MFPackage):
    """Preconditioned Conjugate-Gradient Package"""


class DE4(_MFPackage):
    """Direct Solution Package"""


class SMS(_MFPackage):
    """Sparse Matrix Solver"""


class CLN(_MFPackage):
    """Connected Linear Network Process"""


class GNC(_MFPackage):
    """Ghost Node Correction Package"""


class IBS(_MFPackage):
    """Interbed-Storage Package"""


class LMG(_MFPackage):
    """Link-AMG Package"""


class NWT(_MFPackage):
    """Newton Solver (MODFLOW-NWT only)"""


class LAK(_MFPackage):
    """Lake Package"""


class GAGE(_MFPackage):
    """Gage Package"""


class ETS(_MFPackage):
    """Evapotranspiration Segments Package"""


class DRT(_MFPackage):
    """Drain Return Package"""


class FHB(_MFPackage):
    """Flow and Head Boundary Package"""


class HYD(_MFPackage):
    """HYDMOD Package"""


class RES(_MFPackage):
    """Reservoir Package"""


class MNW(_MFPackage):
    """Multi-Node, Drawdown-Limited Well Package"""


class MNW1(MNW):
    """Multi-Node Well Package version 1"""


class MNW2(_MFPackage):
    """Multi-Node Well Package version 2"""


class MNWI(_MFPackage):
    """Multi-Node Well Information Package"""


class DAF(_MFPackage):
    """DAFLOW Package surface-water input file"""


class DAFG(_MFPackage):
    """DAFLOW Package ground-water input file"""


class STR(_MFPackage):
    """Stream Package"""


class SFR(_MFPackage):
    """Streamflow-Routing Package"""


class SWR(_MFPackage):
    """Surface-Water Routing Package"""


class KDEP(_MFPackage):
    """Hydraulic-Conductivity Depth-Dependence Capability of the HUF2 Package
    """


class LVDA(_MFPackage):
    """Model-Layer Variable-Direction Horizontal Anisotropy capability of the
    HUF2 Package"""


class SUB(_MFPackage):
    """Subsidence and Aquifer-System Compaction Package"""


class SWI2(_MFPackage):
    """Saltwater Intrusion Package"""


class LMT6(_MFPackage):
    """Link-MT3DMS Package"""


class OBS(_MFPackage):
    """Observation Process input file (MODFLOW-2000 only)"""


class ADV2(_MFPackage):
    """Advective-Transport Observation Input File (MODFLOW-2000 only)"""


class CHOB(_MFPackage):
    """Constant-Head Flow Observation Input File"""


class DROB(_MFPackage):
    """Drain Observation Input File"""


class DTOB(_MFPackage):
    """Drain Return Observation Input File (MODFLOW-2000 only)"""


class GBOB(_MFPackage):
    """General-Head-Boundary Observation Input File"""


class HOB(_MFPackage):
    """Head-Observation Input File"""


class RVOB(_MFPackage):
    """River Observation Input File"""


class STOB(_MFPackage):
    """Streamflow-Routing Observation Input File (MODFLOW-2000 only)"""


class CFP(_MFPackage):
    """Conduit Flow Process (MODFLOW-CFP only)"""


class CRCH(_MFPackage):
    """Conduit Recharge Package (MODFLOW-CFP only)"""


class COC(_MFPackage):
    """Conduit Output Control File (MODFLOW-CFP only)"""


class SEN(_MFPackage):
    """Sensitivity Process input file (MODFLOW-2000 only)"""


class PES(_MFPackage):
    """Parameter Estimation Process input file (MODFLOW-2000 only)"""


class _MFData(object):
    pass


class GLOBAL(_MFData):
    """Global listing file. MODFLOW-2000 only."""


class LIST(_MFData):
    """Forward run listing file."""


def _get_packages():
    """Returns a dict of MODFLOW packages supported by moflow.mf"""
    global_dict = globals()
    packages = {}
    for key in global_dict:
        if key.startswith('_'):
            continue
        obj = global_dict[key]
        if inspect.isclass(obj) and issubclass(obj, (_MFPackage, _MFData)):
            packages[key] = obj
    return packages


class Modflow(object):
    """Parent class for MODFLOW packages

    Each package can attach to this object as a lower-case attribute name
    of the package name.

    Example:
    >>> m = Modflow()
    >>> m.dis = DIS()
    >>> m.bas6 = BAS6()
    """

    @property
    def ref_dir(self):
        """Returns reference directory for MODFLOW files"""
        return getattr(self, '_ref_dir', os.getcwd())

    @ref_dir.setter
    def ref_dir(self, value):
        path = str(value)
        if not os.path.isdir(path):
            self._logger.error("'ref_dir' is not a directory: '%s'", path)
        setattr(self, '_ref_dir', path)

    @property
    def prefix(self):
        """Returns prefix name of MODFLOW simulation files"""
        return getattr(self, '_prefix', None)

    @prefix.setter
    def prefix(self, value):
        if value is not None:
            if 'upper' not in value:
                raise ValueError("'prefix' is not string-like")
            elif ' ' in value:
                raise ValueError("spaces found in 'prefix' value")
        setattr(self, '_prefix', value)

    _logger = None
    _packages = None  # _MFPackage objects
    data = None  # _MFData objects

    def __init__(self, *args, **kwargs):
        """Create a MODFLOW simulation"""
        # Set up logger
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.handlers = logger.handlers
        self._logger.setLevel(logger.level)
        self._packages = []
        self.data = {}
        if args:
            self._logger.error("'args' do nothing at the moment: %r", args)
        if kwargs:
            self._logger.error("'kwargs' do nothing at the moment: %r", kwargs)

    def __repr__(self):
        """Representation of Modflow object, showing packages"""
        return '<%s: %s>' % (self.__class__.__name__, ', '.join(list(self)))

    def __len__(self):
        """Returns number of packages"""
        return len(self._packages)

    def __iter__(self):
        """Allow iteration through sequence of packages"""
        return iter(self._packages)

    def __setattr__(self, name, value):
        """Sets Modflow package object"""
        existing = getattr(self, name, None)
        if ((hasattr(self, name) or name.startswith('_')) and
                not isinstance(existing, _MFPackage)):
            # Set existing, non-Modflow package object as normal
            object.__setattr__(self, name, value)
        elif isinstance(value, _MFPackage):
            if name != value.__class__.__name__.lower():
                raise AttributeError("%r must have an attribute name %r" %
                                     (value.__class__.__name__,
                                      value.__class__.__name__.lower()))
            elif existing and existing.__class__ != value.__class__:
                self._logger.warn('attribute %r: replacing value of %r '
                                  ' with %r', name, existing.__class__,
                                  value.__class__)
            if name not in self._packages:
                self._packages.append(name)
                self._logger.debug('attribute %r: adding %r package',
                                   name, value.__class__.__name__)
                if isinstance(existing, _MFPackage):
                    self._logger.error('attribute %r: existed before, but was '
                                       'not found in _packages list', name)
            else:
                if existing is None:
                    self._logger.error('attribute %r: existed in _packages '
                                       'before it was an attribute', name)
                else:
                    self._logger.debug('attribute %r: replacing %r with '
                                       'different object', name,
                                       value.__class__.__name__)
            object.__setattr__(self, name, value)
        else:
            raise ValueError(("attribute %r (%r) must be a _MFPackage object "
                              "or other existing attribute.") % (name, value))

    def __delattr__(self, name):
        """Deletes package object"""
        self._logger.debug('delattr %r', name)
        if name in self._packages:
            del self._packages[self._packages.index(name)]
        object.__delattr__(self, name)

    def append(self, package):
        """Append a package to the end, using a default attribute"""
        if not isinstance(package, _MFPackage):
            raise ValueError("value must be a _MFPackage-related object; "
                             "found " + repr(package.__class__))
        name = package._attr_name
        if hasattr(self, name):
            raise ValueError(
                "attribute %r already exists; use setattr to replace" % name)
        setattr(self, name, package)

    def read(self, fname, **kwargs):
        """Read a MODFLOW simulation from a Name File (with *.nam extension)

        Use 'ref_dir' keyword to specify the reference directory relative to
        other files referenced in the Name File, otherwise it is assumed
        to be relative to the same as the Name File.
        """
        self._logger.info('reading Name File: %s', fname)
        with open(fname, 'r') as fp:
            lines = fp.readlines()
        if 'ref_dir' in kwargs:
            self.ref_dir = kwargs.pop('ref_dir')
            if self.ref_dir is None or not os.path.isdir(str(self.ref_dir)):
                self._logger.error("'ref_dir' is not a directory: %s",
                                   self.ref_dir)
                self.ref_dir = os.path.dirname(fname)
        else:
            self.ref_dir = os.path.dirname(fname)
        if kwargs:
            self._logger.warn('unused keyword arguments: %r', kwargs)
        # Use a separate logger to read the Name File
        log = logging.getLogger('NameFile')
        log.handlers = logger.handlers
        log.setLevel(logger.level)
        self._packages = []
        all_nunit = {}  # check unique Nunit values
        available_packages = _get_packages()
        Dch = {}  # directory cache
        for ln, line in enumerate(lines, start=1):
            line = line.rstrip()
            if len(line) == 0:
                log.debug('%d: skipping empty line', ln)
                continue
            elif len(line) > 199:
                log.warn('%d: has %d characters, but should be <= 199',
                         ln, len(line))
            if line.startswith('#'):
                log.debug('%d: skipping comment: %s', ln, line[1:])
                continue
            # Data Set 1: Ftype Nunit Fname [Option]
            dat = line.split()
            if len(dat) < 3:
                raise ValueError(
                    'line %d has %d items, but 3 or 4 are expected' %
                    (ln, len(dat)))
            ftype, nunit, fname = dat[:3]
            if len(dat) >= 4:
                option = dat[3].upper()
            else:
                option = None
            if len(dat) > 4:
                log.info('%d: ignoring remaining items: %r', ln, dat[4:])
            # Ftype is the file type, which may be entered in all uppercase,
            # all lowercase, or any combination.
            ftype = ftype.upper()
            if ftype.startswith('DATA'):
                obj = _MFData()
            elif ftype in available_packages:
                obj = available_packages[ftype]()
                assert obj.__class__.__name__ == ftype,\
                    (obj.__class__.__name__, ftype)
            else:
                log.warn("%d:ftype: %r not identified as a supported "
                         "file type", ln, ftype)
                obj = _MFPackage()
            obj.parent = self  # set back-reference
            obj.nunit = nunit
            if obj.nunit and obj.nunit in all_nunit:
                log.warn("%d:nunit: %r already assigned for %r",
                         ln, all_nunit[obj.nunit])
            else:
                all_nunit[obj.nunit] = ftype
            obj.fname = fname
            obj.fpath = os.path.join(self.ref_dir, obj.fname)
            fpath_exists = os.path.isfile(obj.fpath)
            if not fpath_exists:
                testDir, test_fname = os.path.split(obj.fname)
                pth = os.path.join(self.ref_dir, testDir)
                if os.path.isdir(pth):
                    if pth not in Dch:
                        Dch[pth] = dict([(f.lower(), f) for f
                                         in os.listdir(pth)])
                    test_fname = test_fname.lower()
                    if test_fname in Dch[pth]:
                        fpath_exists = True
                        obj.fname = os.path.join(testDir, Dch[pth][test_fname])
                        log.info("%d:fname: changing to '%s'", ln, obj.fname)
                        obj.fpath = os.path.join(pth, test_fname)
            if isinstance(obj, _MFPackage) and not fpath_exists:
                log.warn("%d:fname: '%s' does not exist in '%s'",
                         ln, obj.fname, self.ref_dir)
            # Interpret option
            if option == 'OLD':
                # the file must exist when MODFLOW has started
                if ftype.startswith('DATA') and not fpath_exists:
                    log.warn("%d:option:%r, but file does not exist",
                             ln, option)
            elif option == 'REPLACE':
                if ftype.startswith('DATA') and fpath_exists:
                    log.debug("%d:option:%r: file exists and will be replaced",
                              ln, option)
            obj.nam_option = option
            if isinstance(obj, _MFPackage):
                setattr(self, obj._attr_name, obj)
        log.debug('finished reading %d lines', ln)
        del log
        self._logger.info('reading data from %d packages', len(self))
        for name in self._packages:
            package = getattr(self, name)
            try:
                package.read()
            except NotImplementedError:
                self._logger.info("'read' for %r not implemented", name)
