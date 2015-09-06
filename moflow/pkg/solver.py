"""Solvers
"""
__all__ = [
    'DE4', 'GMG', 'LMG', 'PCG', 'SIP', 'SOR', 'NWT', 'SMS'
]

from .base import _MFPackage


class DE4(_MFPackage):
    """Direct Solution Package"""


class GMG(_MFPackage):
    """GMG - Geometric Multigrid Solver"""


class LMG(_MFPackage):
    """Link-AMG Package"""


class PCG(_MFPackage):
    """Preconditioned Conjugate-Gradient Package"""


class SIP(_MFPackage):
    """Strongly Implicit Procedure Package"""


class SOR(_MFPackage):
    """Slice-Successive Over-Relaxation Package"""


class NWT(_MFPackage):
    """Newton Solver (MODFLOW-NWT only)"""


class SMS(_MFPackage):
    """Sparse Matrix Solver (>= MODFLOW-USG)"""
