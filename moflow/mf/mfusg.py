"""Unstructured Grids (MODFLOW-USG only)
"""

from .base import MFPackage


__all__ = ['CLN', 'GNC']


class CLN(MFPackage):
    """Connected Linear Network Process"""


class GNC(MFPackage):
    """Ghost Node Correction Package"""
