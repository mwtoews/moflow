"""Output Control."""

from .base import MFPackage

__all__ = ["GAGE", "HYD", "LMT6", "MNWI", "OC", "LIST"]


class GAGE(MFPackage):
    """Gage Package."""


class HYD(MFPackage):
    """HYDMOD Package."""


class LMT6(MFPackage):
    """Link-MT3DMS Package."""


class MNWI(MFPackage):
    """Multi-Node Well Information Package."""


class OC(MFPackage):
    """Output Control Option."""


class LIST(MFPackage):
    """Forward run listing file."""
