import base

from .out import GAGE, HYD, LMT6, MNWI, OC, LIST
from .dis import DIS, DISU
from bas import *
from gwfp import *
from .bc import *
import solver
import subs
import cfp
import swr
import mf2k
import usg


def _all_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                   for g in _all_subclasses(s)]

class_dict = {
    cls.__name__: cls for cls in _all_subclasses(base._MFPackage)
    if not cls.__name__.startswith('_')}
