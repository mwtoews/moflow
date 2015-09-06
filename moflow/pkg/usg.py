"""Unstructured Grids (MODFLOW-USG only)
"""

__all__ = ['CLN', 'GNC']

from .base import _MFPackage


class CLN(_MFPackage):
    """Connected Linear Network Process"""


class GNC(_MFPackage):
    """Ghost Node Correction Package"""
