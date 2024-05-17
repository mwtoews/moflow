"""Conduit Flow Process  (MODFLOW-CFP only)."""

from .base import MFPackage

__all__ = ["CFP", "CRCH", "COC"]


class CFP(MFPackage):
    """Conduit Flow Process."""


class CRCH(MFPackage):
    """Conduit Recharge Package."""


class COC(MFPackage):
    """Conduit Output Control File."""
