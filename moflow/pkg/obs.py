"""Observation Process
"""

__all__ = [
    'CHOB', 'DROB', 'DTOB', 'GBOB', 'OBS', 'HOB', 'RVOB', 'STOB'
]

from .base import MFPackage


class CHOB(MFPackage):
    """Constant-Head Flow Observation Input File"""


class DROB(MFPackage):
    """Drain Observation Input File"""


class DTOB(MFPackage):
    """Drain Return Observation Input File (MODFLOW-2000 only)"""


class GBOB(MFPackage):
    """General-Head-Boundary Observation Input File"""


class OBS(MFPackage):
    """Observation Process input file (MODFLOW-2000 only)"""


class HOB(MFPackage):
    """Head-Observation Input File"""


class RVOB(MFPackage):
    """River Observation Input File"""


class STOB(MFPackage):
    """Stream Observation Input File (MODFLOW-2000 only)"""
