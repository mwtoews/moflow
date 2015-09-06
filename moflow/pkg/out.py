"""Output Control
"""

__all__ = [
    'GAGE', 'HYD', 'LMT6', 'MNWI', 'OC', 'LIST'
]

from .base import _MFPackage


class GAGE(_MFPackage):
    """Gage Package"""


class HYD(_MFPackage):
    """HYDMOD Package"""


class LMT6(_MFPackage):
    """Link-MT3DMS Package"""


class MNWI(_MFPackage):
    """Multi-Node Well Information Package"""


class OC(_MFPackage):
    """Output Control Option"""


class LIST(_MFPackage):
    """Forward run listing file."""
