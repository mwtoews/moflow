"""Boundary Condition Packages
"""

__all__ = [
    'BFH', 'CHD',
    'FHB', 'RCH', 'WEL',
    'DRN', 'DRT', 'ETS', 'EVT', 'GHB', 'LAK', 'MNW', 'MNW1', 'MNW2',
    'RES', 'RIV', 'SFR', 'STR',
]

from .base import _MFPackage


# Specified Head Boundaries

class BFH(_MFPackage):
    """Boundary Flow and Head Package"""


class CHD(_MFPackage):
    """Ground-Water Flow Process Time-Variant Specified-Head Package"""


# Specified Flux Boundaries

class FHB(_MFPackage):
    """Flow and Head Boundary Package"""

from .rch import RCH


class WEL(_MFPackage):
    """Ground-Water Flow Process Well Package"""


# Head-Dependent Flux Boundary Packages

class DAF(_MFPackage):
    """DAFLOW Package surface-water input file"""


class DAFG(_MFPackage):
    """DAFLOW Package ground-water input file"""


class DRN(_MFPackage):
    """Ground-Water Flow Process Drain Package"""


class DRT(_MFPackage):
    """Drain Return Package"""


class ETS(_MFPackage):
    """Evapotranspiration Segments Package"""


class EVT(_MFPackage):
    """Ground-Water Flow Process Evapotranspiration Package"""


class GHB(_MFPackage):
    """Ground-Water Flow Process General-Head Boundary Package"""


class LAK(_MFPackage):
    """Lake Package"""


class MNW(_MFPackage):
    """Multi-Node, Drawdown-Limited Well Package"""


class MNW1(MNW):
    """Multi-Node Well Package version 1"""


class MNW2(_MFPackage):
    """Multi-Node Well Package version 2"""


class RES(_MFPackage):
    """Reservoir Package"""


class RIV(_MFPackage):
    """Ground-Water Flow Process River Package"""


class SFR(_MFPackage):
    """Streamflow-Routing Package"""


class STR(_MFPackage):
    """Stream Package"""


class UZF(_MFPackage):
    """Ground-Water Flow Process Unsaturated-Zone Flow Package"""
