"""Conduit Flow Process  (MODFLOW-CFP only)
"""

__all__ = ['CFP', 'CRCH', 'COC']

from .base import _MFPackage


class CFP(_MFPackage):
    """Conduit Flow Process"""


class CRCH(_MFPackage):
    """Conduit Recharge Package"""


class COC(_MFPackage):
    """Conduit Output Control File"""
