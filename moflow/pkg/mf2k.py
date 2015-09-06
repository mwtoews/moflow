"""MODFLOW-2000 only
"""

__all__ = ['GLOBAL', 'ADV2', 'SEN', 'PES']

from .base import _MFPackage, MFData


class GLOBAL(MFData):
    """Global listing file"""


class ADV2(_MFPackage):
    """Advective-Transport Observation Input File"""


class SEN(_MFPackage):
    """Sensitivity Process input file"""


class PES(_MFPackage):
    """Parameter Estimation Process input file"""
