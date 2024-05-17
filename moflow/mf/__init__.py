from . import base


def _all_subclasses(cls):
    return cls.__subclasses__() + [
        g for s in cls.__subclasses__() for g in _all_subclasses(s)
    ]


class_dict = {
    cls.__name__: cls
    for cls in _all_subclasses(base.MFPackage)
    if not cls.__name__.startswith("_")
}
