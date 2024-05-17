import os

from .._logger import logger, logging
from . import class_dict
from .base import MFData, MFPackage


class Modflow:
    """Base class for MODFLOW packages, based on Name File (NAM).

    Each package can attach to this object as a lower-case attribute name
    of the package name.

    Example:
    -------
    >>> m = Modflow()
    >>> m.dis = DIS()
    >>> m.bas6 = BAS6()

    """

    @property
    def ref_dir(self):
        """Returns reference directory for MODFLOW files."""
        return getattr(self, "_ref_dir", "")

    @ref_dir.setter
    def ref_dir(self, value) -> None:
        path = str(value)
        if path and not os.path.isdir(path):
            self._logger.error("'ref_dir' is not a directory: '%s'", path)
        self._ref_dir = path

    @property
    def prefix(self):
        """Returns prefix name of MODFLOW simulation files."""
        return getattr(self, "_prefix", None)

    @prefix.setter
    def prefix(self, value) -> None:
        if value is not None:
            if "upper" not in value:
                raise ValueError("'prefix' is not string-like")
            elif " " in value:
                raise ValueError("spaces found in 'prefix' value")
        self._prefix = value

    _logger = None
    _packages = None  # MFPackage objects
    _nunit = None  # keys are integer nunit of either fpath str or file object
    data = None  # MFData objects

    def __init__(self, *args, **kwargs) -> None:
        """Create a MODFLOW simulation."""
        # Set up logger
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.handlers = logger.handlers
        self._logger.setLevel(logger.level)
        self._packages = []
        self._nunit = {}
        self.data = {}
        if args:
            self._logger.error("'args' do nothing at the moment: %r", args)
        if kwargs:
            self._logger.error("'kwargs' do nothing at the moment: %r", kwargs)

    def __repr__(self) -> str:
        """Representation of Modflow object, showing packages."""
        return "<%s: %s>" % (self.__class__.__name__, ", ".join(list(self)))

    def __getitem__(self, key):
        """Return package or data using nunit integer."""
        return self._nunit[key]

    def __setitem__(self, key, value) -> None:
        """Set package or data with nunit integer."""
        self._nunit[key] = value

    def __len__(self) -> int:
        """Returns number of packages, but not data or nunit items."""
        return len(self._packages)

    def __iter__(self):
        """Allow iteration through sequence of packages, but not data."""
        return iter(self._packages)

    def __setattr__(self, name, value) -> None:
        """Sets Modflow package object."""
        existing = getattr(self, name, None)
        if (hasattr(self, name) or name.startswith("_")) and not isinstance(
            existing, MFPackage,
        ):
            # Set existing, non-Modflow package object as normal
            object.__setattr__(self, name, value)
        elif isinstance(value, MFPackage):
            if name != value.__class__.__name__.lower():
                raise AttributeError(
                    "%r must have an attribute name %r"
                    % (value.__class__.__name__, value.__class__.__name__.lower()),
                )
            elif existing and existing.__class__ != value.__class__:
                self._logger.warning(
                    "attribute %r: replacing value of %r  with %r",
                    name,
                    existing.__class__,
                    value.__class__,
                )
            if name not in self._packages:
                self._packages.append(name)
                self._logger.debug(
                    "attribute %r: adding %r package", name, value.__class__.__name__,
                )
                if isinstance(existing, MFPackage):
                    self._logger.error(
                        "attribute %r: existed before, but was "
                        "not found in _packages list",
                        name,
                    )
            elif existing is None:
                self._logger.error(
                    "attribute %r: existed in _packages "
                    "before it was an attribute",
                    name,
                )
            else:
                self._logger.debug(
                    "attribute %r: replacing %r with different object",
                    name,
                    value.__class__.__name__,
                )
            object.__setattr__(self, name, value)
        else:
            raise ValueError(
                (
                    f"attribute {name!r} ({value!r}) must be a MFPackage object "
                    "or other existing attribute."
                ),
            )

    def __delattr__(self, name) -> None:
        """Deletes package object."""
        self._logger.debug("delattr %r", name)
        if name in self._packages:
            del self._packages[self._packages.index(name)]
        object.__delattr__(self, name)

    def append(self, package) -> None:
        """Append a package to the end, using a default attribute."""
        if not isinstance(package, MFPackage):
            raise ValueError(
                "value must be a MFPackage-related object; "
                f"found {package.__class__!r}",
            )
        name = package._attr_name
        if hasattr(self, name):
            raise ValueError(
                f"attribute {name!r} already exists; use setattr to replace",
            )
        setattr(self, name, package)
        if package.nam is None:
            package.nam = self
        elif package.nam is self:
            self._logger.debug("%s.nam already set", name)
        else:
            self._logger.error(
                "not setting %s.nam, since it is already assigned to %r",
                name,
                package.nam,
            )
        if package.nunit:
            self[package.nunit] = package

    def read(self, fname, *args, **kwargs) -> None:
        """Read a MODFLOW simulation from a Name File (with *.nam extension).

        Use 'ref_dir' keyword to specify the reference directory relative to
        other files referenced in the Name File, otherwise it is assumed
        to be relative to the same as the Name File.
        """
        self._packages = []
        self._nunit = {}
        self.data = {}
        self._logger.info("reading Name File: %s", fname)
        with open(fname) as fp:
            lines = fp.readlines()
        if "ref_dir" in kwargs:
            self.ref_dir = kwargs.pop("ref_dir")
            if self.ref_dir is None or not os.path.isdir(str(self.ref_dir)):
                self._logger.error("'ref_dir' is not a directory: %s", self.ref_dir)
                self.ref_dir = os.path.dirname(fname)
        else:
            self.ref_dir = os.path.dirname(fname)
        if args:
            self._logger.warning("unused arguments: %r", args)
        if kwargs:
            self._logger.warning("unused keyword arguments: %r", kwargs)
        # Use a separate logger to read the Name File
        log = logging.getLogger("NameFile")
        log.handlers = logger.handlers
        log.setLevel(logger.level)
        self._packages = []
        dir_cache = {}
        for ln, line in enumerate(lines, start=1):
            line = line.rstrip()
            if len(line) == 0:
                log.debug("%d: skipping empty line", ln)
                continue
            elif len(line) > 199:
                log.warning("%d: has %d characters, but should be <= 199", ln, len(line))
            if line.startswith("#"):
                log.debug("%d: skipping comment: %s", ln, line[1:])
                continue
            # 1: Ftype Nunit Fname [Option]
            dat = line.split()
            if len(dat) < 3:
                raise ValueError(
                    "line %d has %d items, but 3 or 4 are expected" % (ln, len(dat)),
                )
            ftype, nunit, fname = dat[:3]
            if len(dat) >= 4:
                option = dat[3].upper()
            else:
                option = None
            if len(dat) > 4:
                log.info("%d: ignoring remaining items: %r", ln, dat[4:])
            # Ftype is the file type, which may be entered in all uppercase,
            # all lowercase, or any combination.
            ftype = ftype.upper()
            if ftype.startswith("DATA"):
                obj = MFData()
            elif ftype in class_dict:
                obj = class_dict[ftype]()
                assert obj.__class__.__name__ == ftype, (obj.__class__.__name__, ftype)
            else:
                log.warning(
                    "%d:ftype: %r not identified as a supported file type", ln, ftype,
                )
                obj = MFPackage()
            # set back-references for NameFile and Nunit
            obj.nam = self
            obj.nunit = nunit = int(nunit)
            try:
                self[nunit] = obj
            except KeyError:
                log.warning(
                    "%d:nunit: %s already assigned for %r",
                    ln,
                    nunit,
                    self[nunit].__class__.__name__,
                )
            orig_fname = fname
            fname = fname.strip('"')
            if os.path.sep == "/":  # for reading on POSIX systems
                if "\\" in fname:
                    fname = fname.replace("\\", "/")
            fpath = os.path.join(self.ref_dir, fname)
            if not os.path.isfile(fpath):
                test_dir, test_fname = os.path.split(fname)
                pth = os.path.join(self.ref_dir, test_dir)
                if os.path.isdir(pth):
                    if pth not in dir_cache:
                        dir_cache[pth] = dict([(f.lower(), f) for f in os.listdir(pth)])
                    fname_key = test_fname.lower()
                    if fname_key in dir_cache[pth]:
                        fname = os.path.join(test_dir, dir_cache[pth][fname_key])
                        fpath = os.path.join(pth, dir_cache[pth][fname_key])
                        assert os.path.isfile(fpath), fpath
            if orig_fname != fname:
                log.info("%d:fname: changed from '%s' to '%s'", ln, orig_fname, fname)
            obj.fname = fname
            obj.fpath = fpath
            fpath_exists = os.path.isfile(obj.fpath)
            if isinstance(obj, MFPackage) and not fpath_exists:
                log.warning(
                    "%d:fname: '%s' does not exist in '%s'", ln, obj.fname, self.ref_dir,
                )
            # Interpret option
            if option == "OLD":
                # the file must exist when MODFLOW has started
                if ftype.startswith("DATA") and not fpath_exists:
                    log.warning("%d:option:%r, but file does not exist", ln, option)
            elif option == "REPLACE":
                if ftype.startswith("DATA") and fpath_exists:
                    log.debug(
                        "%d:option:%r: file exists and will be replaced", ln, option,
                    )
            obj.nam_option = option
            if isinstance(obj, MFPackage):
                setattr(self, obj._attr_name, obj)
        log.debug("finished reading %d lines", ln)
        del log
        self._logger.info("reading data from %d packages", len(self))
        # Read prerequisite packages first
        if hasattr(self, "dis"):
            dis_mode = "dis"
        elif hasattr(self, "disu"):
            dis_mode = "disu"
        else:
            self._logger.error("'DIS' or 'DISU' not in Name file!")
        dis_obj = getattr(self, dis_mode)
        dis_obj.read()
        for name in self._packages:
            if name == dis_mode:
                continue
            package = getattr(self, name)
            # Set prerequisite attributes before reading
            if hasattr(package, dis_mode):
                setattr(package, dis_mode, dis_obj)
            try:
                package.read()
            except NotImplementedError:
                self._logger.info("'read' for %r not implemented", name)
