# -*- coding: utf-8 -*-
"""
Modflow module
"""

import os
import inspect

from . import logger, logging


class _MFPackage(object):
    """The inherrited ___class__.__name__ is the Fname of the package, which
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
    def Nunit(self):
        """Nunit is the Fortran unit to be used when reading from or writing
        to the file. Any legal unit number on the computer being used can
        be specified except units 96-99. Unspecified is unit 0."""
        return getattr(self, '_Nunit', 0)

    @Nunit.setter
    def Nunit(self, value):
        if value is None:
            value = 0
        else:
            try:
                value = int(value)
            except ValueError:
                self._logger.error("Nunit: %r is not an integer", value)
        if value >= 96 and value <= 99:
            self._logger.error("Nunit: %r is not valid", value)
        setattr(self, '_Nunit', value)

    @property
    def Fname(self):
        """Fname is the name of the file, which is a character value.
        Pathnames may be specified as part of Fname. However, space characters
        are not allowed in Fname."""
        return getattr(self, '_Fname', None)

    @Fname.setter
    def Fname(self, value):
        if value is not None:
            if ' ' in value:
                self._logger.warn("Fname: %d space characters found in %r",
                                  value.count(' '), value)
            if os.path.sep == '/':  # for reading on POSIX systems
                if '\\' in value:
                    self._logger.info(r"Fname: replacing '\' with '/' path "
                                      "separators to read file on host system")
                    value = value.replace('\\', '/')
        self._Fname = value

    @property
    def NamOption(self):
        """Returns 'Option' for Name File, which can be: OLD, REPLACE, UNKNOWN
        """
        return getattr(self, '_NamOption', None)

    @NamOption.setter
    def NamOption(self, value):
        if hasattr(value, 'upper') and value.upper() != value:
            self._logger.info('NamOption: changing value from %r to %r',
                              value, value.upper())
            value = value.upper()
        expected = [None, 'OLD', 'REPLACE', 'UNKNOWN']
        if value not in expected:
            self._logger.error("NamOption: %r is not valid; expecting one of "
                               "%r", value, expected)
        self._NamOption = value

    def read(self, *args, **kwargs):
        raise NotImplementedError("'read' not implemented for " +
                                  repr(self.__class__.__name__))

    def write(self, *args, **kwargs):
        raise NotImplementedError("'write' not implemented for " +
                                  repr(self.__class__.__name__))

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
    of the package Ftype.

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
        """Append a pacage to the end, usign a default attribute"""
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
        allNunit = {}  # check unique Nunit values
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
            Ftype, Nunit, Fname = dat[:3]
            if len(dat) >= 4:
                Option = dat[3].upper()
            else:
                Option = None
            if len(dat) > 4:
                log.info('%d: ignoring remaining items: %r', ln, dat[4:])
            # Ftype is the file type, which may be entered in all uppercase,
            # all lowercase, or any combination.
            Ftype = Ftype.upper()
            if Ftype.startswith('DATA'):
                obj = _MFData()
            elif Ftype in available_packages:
                obj = available_packages[Ftype]()
                assert obj.__class__.__name__ == Ftype,\
                    (obj.__class__.__name__, Ftype)
            else:
                log.warn("%d:Ftype: %r not identified as a supported "
                         "file type", ln, Ftype)
                obj = _MFPackage()
            obj.parent = self  # set back-reference
            obj.Nunit = Nunit
            if obj.Nunit and obj.Nunit in allNunit:
                log.warn("%d:Nunit: %r already assigned for %r",
                         ln, allNunit[obj.Nunit])
            else:
                allNunit[obj.Nunit] = Ftype
            obj.Fname = Fname
            obj.Fpath = os.path.join(self.ref_dir, obj.Fname)
            Fpath_exists = os.path.isfile(obj.Fpath)
            if not Fpath_exists:
                testDir, testFname = os.path.split(obj.Fname)
                pth = os.path.join(self.ref_dir, testDir)
                if os.path.isdir(pth):
                    if pth not in Dch:
                        Dch[pth] = dict([(f.lower(), f) for f
                                         in os.listdir(pth)])
                    testFname = testFname.lower()
                    if testFname in Dch[pth]:
                        Fpath_exists = True
                        obj.Fname = os.path.join(testDir, Dch[pth][testFname])
                        log.info("%d:Fname: changing to '%s'", ln, obj.Fname)
                        obj.Fpath = os.path.join(pth, testFname)
            if isinstance(obj, _MFPackage) and not Fpath_exists:
                log.warn("%d:Fname: '%s' does not exist in '%s'",
                         ln, obj.Fname, self.ref_dir)
            # Interpret Option
            if Option == 'OLD':
                # the file must exist when the MF is started
                if Ftype.startswith('DATA') and not Fpath_exists:
                    log.warn("%d:Option:%r, but file does not exist",
                             ln, Option)
            elif Option == 'REPLACE':
                if Ftype.startswith('DATA') and Fpath_exists:
                    log.debug("%d:Option:%r: file exists and will be replaced",
                              ln, Option)
            obj.NamOption = Option
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
