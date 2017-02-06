"""Ground-Water Flow Process
"""

from .base import MFPackage


__all__ = [
    'MULT', 'ZONE', 'PVAL',
    'BCF6', 'LPF', 'HUF2', 'UPW', 'HFB6', 'SWI2'
]


# Ground-Water Flow Process

class MULT(MFPackage):
    """Multiplier array file"""


class ZONE(MFPackage):
    """Zone array"""


class PVAL(MFPackage):
    """Parameter Value file"""


# Ground-Water Flow Packages

class BCF6(MFPackage):
    """Block-Centered Flow Package"""


class LPF(MFPackage):
    """Layer Property Flow Package"""


class HUF2(MFPackage):
    """Hydrogeologic Unit Flow Package"""


class KDEP(MFPackage):
    """Hydraulic-Conductivity Depth-Dependence Capability of the HUF2 Package
    """


class LVDA(MFPackage):
    """Model-Layer Variable-Direction Horizontal Anisotropy capability of the
    HUF2 Package"""


class UPW(MFPackage):
    """Upstream Weighting Package (MODFLOW-NWT only)"""


class HFB6(MFPackage):
    """Horizontal Flow Barrier Package"""


class SWI2(MFPackage):
    """Saltwater Intrusion Package"""
