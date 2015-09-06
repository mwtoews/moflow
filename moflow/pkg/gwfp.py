"""Ground-Water Flow Process
"""

__all__ = [
    'MULT', 'ZONE', 'PVAL',
    'BCF6', 'LPF', 'HUF2', 'UPW', 'HFB6', 'SWI2'
]

from .base import _MFPackage


# Ground-Water Flow Process

class MULT(_MFPackage):
    """Multiplier array file"""


class ZONE(_MFPackage):
    """Zone array"""


class PVAL(_MFPackage):
    """Parameter Value file"""


# Ground-Water Flow Packages

class BCF6(_MFPackage):
    """Block-Centered Flow Package"""


class LPF(_MFPackage):
    """Layer Property Flow Package"""


class HUF2(_MFPackage):
    """Hydrogeologic Unit Flow Package"""


class KDEP(_MFPackage):
    """Hydraulic-Conductivity Depth-Dependence Capability of the HUF2 Package
    """


class LVDA(_MFPackage):
    """Model-Layer Variable-Direction Horizontal Anisotropy capability of the
    HUF2 Package"""


class UPW(_MFPackage):
    """Upstream Weighting Package (MODFLOW-NWT only)"""


class HFB6(_MFPackage):
    """Horizontal Flow Barrier Package"""


class SWI2(_MFPackage):
    """Saltwater Intrusion Package"""
