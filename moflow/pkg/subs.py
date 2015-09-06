"""Subsidence
"""
__all__ = [
    'IBS', 'SUB', 'SWT'
]

from .base import _MFPackage


class IBS(_MFPackage):
    """Interbed-Storage Package"""


class SUB(_MFPackage):
    """Subsidence and Aquifer-System Compaction Package"""


class SWT(_MFPackage):
    """Subsidence and Aquifer-System Compaction Package for Water-Table
    Aquifers"""
