# -*- coding: utf-8 -*-
"""

"""
__version__ = 0.0
__author__ = 'Mike Toews'
__email__ = 'mwtoews@gmail.com'

import os
import sys
import inspect

# set up a module logger
import logging
logger = logging.getLogger('Modflow')
formatter = logging.Formatter(logging.BASIC_FORMAT)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.handlers = [handler]
del formatter, handler


class _MFPackage(object):
    parent = None  # back-reference to Modflow object
    Ftype = None
    Nunit = None
    Fname = None

    @property
    def _default_attrname(self):
        return self.Ftype.lower()

    def read(self, **kwargs):
        raise NotImplementedError("'read' not implemented for " +
                                  repr(self.__class__.__name__))

    def write(self, **kwargs):
        raise NotImplementedError("'write' not implemented for " +
                                  repr(self.__class__.__name__))


class DIS(_MFPackage):
    """Discretization file"""


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
    pass


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
    """Parent class for MODFLOW packages"""
    dir = None
    _logger = None
    _packages = None
    _Nunit = None

    def __init__(self, **kwargs):
        """Create a MODFLOW simulation"""
        # Set up logger
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.handlers = logger.handlers
        self._logger.setLevel(logger.level)
        self._packages = []
        self._Nunit = {}
        if kwargs:
            raise ValueError("'kwargs' do nothing at the moment")

    def read(self, path, **kwargs):
        """Read a MODFLOW simulation from a Name File"""
        self._logger.info('reading Name File %s', path)
        with open(path, 'r') as fp:
            lines = fp.readlines()
        if 'dir' in kwargs:
            self.dir = kwargs.pop('dir')
        else:
            self.dir = os.path.dirname(path)
        if kwargs:
            self._logger.warn('unused keyword arguments: %r', kwargs)
        # Use a separate logger to read the Name File
        log = logging.getLogger('NameFile')
        log.handlers = logger.handlers
        log.setLevel(logger.level)
        self._packages = []
        available_packages = _get_packages()
        D = {}
        for ln, line in enumerate(lines):
            line = line.rstrip()
            if len(line) == 0:
                log.debug('%d: skipping empty line', ln + 1)
                continue
            elif len(line) > 199:
                log.warn('%d: has %d characters, but should be <= 199',
                         ln + 1, len(line))
            if line.startswith('#'):
                log.debug('%d: skipping comment: %s', ln + 1, line[1:])
                continue
            # Data Set 1: Ftype Nunit Fname [Option]
            dat = line.split()
            if len(dat) < 3:
                raise ValueError(
                    'line %d has %d items, but 3 or 4 are expected' %
                    (ln + 1, len(dat)))
            Ftype = dat[0].upper()
            Nunit, Fname = dat[1:3]
            if len(dat) >= 4:
                Option = dat[3]
            else:
                Option = None
            if Ftype.startswith('DATA'):
                log.debug('found %r', Ftype)
                obj = _MFData()
            elif Ftype in available_packages:
                log.debug('setting up %r package data', Ftype)
                obj = available_packages[Ftype]()
            else:
                log.warn("%d:Ftype: %r not identified as a supported "
                         "file type", ln + 1, Ftype)
                obj = _MFPackage()
            obj.parent = self
            obj.Ftype = Ftype
            Fpath = os.path.join(self.dir, Fname)
            if isinstance(obj, _MFPackage) and not os.path.isfile(Fpath):
                file_exists = False
                test_dir, test_fname = os.path.split(Fname.replace('\\', '/'))
                pth = os.path.join(self.dir, test_dir)
                if os.path.isdir(pth):
                    if pth not in D:
                        D[pth] = dict([(f.lower(), f) for f
                                       in os.listdir(pth)])
                    test_fname = test_fname.lower()
                    if test_fname in D[pth]:
                        file_exists = True
                        Fname = os.path.join(test_dir, D[pth][test_fname])
                        log.info("%d:Fname: changing to '%s'", ln + 1, Fname)
                        Fpath = os.path.join(pth, test_fname)
                if not file_exists:
                    log.warn("%d:Fname: '%s' does not exist in '%s'",
                             ln + 1, Fname, self.dir)
            obj.Fname = Fname
            try:
                Nunit = int(Nunit)
            except ValueError:
                log.warn("%d:Nunit: is not an integer; found %r",
                         ln + 1, Nunit)
            # check if unique
            if Nunit:
                if Nunit in self._Nunit:
                    log.warn(
                        "%d:Nunit: %r already assigned for %r package",
                        ln + 1, Nunit, self._Nunit[Nunit].__class__.__name__)
                else:
                    self._Nunit[Nunit] = obj
            obj.Nunit = Nunit
            obj.Option = Option
            if isinstance(obj, _MFPackage):
                setattr(self, obj._default_attrname, obj)
        log.debug('finished reading %d lines', ln + 1)
        del log
        self._logger.info('reading data from %d packages', len(self))
        for name in self._packages:
            package = getattr(self, name)
            try:
                package.read()
            except NotImplementedError:
                self._logger.info("'read' for %r not implemented", name)

    def __len__(self):
        """Returns number of packages"""
        return len(self._packages)

    def __getitem__(self, key):
        """Returns package from index"""
        return self._packages[key]

    def __getattr__(self, name):
        """Returns package object"""
        if not name.startswith('__'):
            self._logger.debug('getattr %r', name)
        try:
            return object.__getattr__(self, name)
        except AttributeError:
            raise AttributeError('%r does not have attribute %r' %
                                 (self.__class__.__name__, name))

    def __setattr__(self, name, value):
        """Sets Modflow package object"""
        #if name != '_logger':
        #    self._logger.debug('setattr %r with %r', name, value)
        object.__setattr__(self, name, value)
        if isinstance(value, _MFPackage):
            self._logger.debug('adding %r package to attribute %r',
                               value.Ftype, name)
            self._packages.append(name)

    def __delattr__(self, name):
        """Deletes package object"""
        self._logger.debug('delattr %r', name)
        if name in self._packages:
            del self._packages[name]
        object.__delattr__(self, name)
