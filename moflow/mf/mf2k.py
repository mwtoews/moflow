"""MODFLOW-2000 only."""

from .base import MFData, MFPackage

__all__ = ["GLOBAL", "ADV2", "SEN", "PES"]


class GLOBAL(MFData):
    """Global listing file."""


class ADV2(MFPackage):
    """Advective-Transport Observation Input File."""


class SEN(MFPackage):
    """Sensitivity Process input file."""


class PES(MFPackage):
    """Parameter Estimation Process input file."""
