"""Output Control."""

from .base import MFPackage
from .mf2k import PES

__all__ = ["ASP", "PES"]


class ASP(MFPackage):
    """PEST-ASP."""
