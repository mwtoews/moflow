"""Subsidence
"""

from .base import MFPackage


__all__ = ['IBS', 'SUB', 'SWT']


class IBS(MFPackage):
    """Interbed-Storage Package"""


class SUB(MFPackage):
    """Subsidence and Aquifer-System Compaction Package"""


class SWT(MFPackage):
    """Subsidence and Aquifer-System Compaction Package for Water-Table
    Aquifers"""
