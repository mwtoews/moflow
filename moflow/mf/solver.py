"""Solvers
"""

from .base import MFPackage


__all__ = ['DE4', 'GMG', 'LMG', 'PCG', 'SIP', 'SOR', 'NWT', 'SMS']


class DE4(MFPackage):
    """Direct Solution Package"""


class GMG(MFPackage):
    """GMG - Geometric Multigrid Solver"""


class LMG(MFPackage):
    """Link-AMG Package"""


class PCG(MFPackage):
    """Preconditioned Conjugate-Gradient Package"""


class SIP(MFPackage):
    """Strongly Implicit Procedure Package"""


class SOR(MFPackage):
    """Slice-Successive Over-Relaxation Package"""


class NWT(MFPackage):
    """Newton Solver (MODFLOW-NWT only)"""


class SMS(MFPackage):
    """Sparse Matrix Solver (>= MODFLOW-USG)"""
