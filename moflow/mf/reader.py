import os
import re

import numpy as np

try:
    import h5py
except ImportError:
    h5py = None

from .._logger import logger, logging
from .base import MFPackage, MissingFile
from .name import Modflow

_re_fmtin = re.compile(
    r"\((?P<body>(?P<rep>\d*)(?P<symbol>[IEFG][SN]?)(?P<w>\d+)(\.(?P<d>\d+))?"
    r"|FREE|BINARY)\)",
)


class MFFileReader:
    """MODFLOW file reader."""

    _parent_class = MFPackage

    def __init__(self, f=None, parent=None) -> None:
        """Initialize with a file and an instance of a parent class.

        Parameters
        ----------
        f : str, file-like object or None
            A path to a file, or a file-like reader with with a 'readlines'
            method, such as BytesIO. If None, then it is obtained from
            parent.fpath, or parent.fname
        parent : instance of MFPackage

        """
        # Set up logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logger.level)
        if parent is None:
            parent = self._parent_class()
        if not isinstance(parent, self._parent_class):
            self.logger.error(
                "'parent' should be an instance of a %r object; found %r",
                self._parent_class.__name__,
                parent.__class__.__name__,
            )
        self.parent = parent
        if f is None:
            if getattr(parent, "fpath", None) is not None:
                f = parent.fpath
            elif getattr(parent, "fname", None) is not None:
                f = parent.fname
            else:
                raise ValueError("unsure how to open file")
        # Read data
        if hasattr(f, "readlines"):
            # it is a file reader object, e.g. BytesIO
            self.fname = f.__class__.__name__
            self.lines = f.readlines()
        else:
            self.fpath = self.parent.fpath = f
            if getattr(self, "fname", None) is None:
                self.fname = os.path.split(self.parent.fpath)[1]
            # Read whole file at once, then close it
            with open(self.parent.fpath) as fp:
                self.lines = fp.readlines()
        if self.parent.nam is None:
            self.parent.nam = Modflow()
            try:
                self.parent.nam.ref_dir = os.path.dirname(self.fpath)
            except:
                pass
        self.logger.info("read file '%s' with %d lines", self.fname, len(self.lines))
        self.lineno = 0
        self.data_set_num = None

    def __len__(self) -> int:
        """Returns number of lines."""
        return len(self.lines)

    def location_exception(self, e):
        """Use to show location of exception while reading file.

        Example:
        -------
        fp = _MFFileReader(fpath, self)
        try:
            fp.read_text(0)
            ...
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))

        """
        location = "%s:%s:%s:Data set %s:" % (
            self.parent.__class__.__name__,
            self.fname,
            self.lineno,
            self.data_set_num,
        )
        return (
            "import sys; raise type(e)(str(e) + '" + location + "' + "
            "str(e)).with_traceback(sys.exc_info()[2])"
        )

    def check_end(self) -> None:
        """Check end of file and show messages in logger on status."""
        if len(self) == self.lineno:
            self.logger.info("finished reading %d lines", self.lineno)
        elif len(self) > self.lineno:
            remain = len(self) - self.lineno
            a, b = "s", ""
            if remain == 1:
                b, a = a, b
            self.logger.warning(
                "finished reading %d lines, but %d line%s remain%s",
                self.lineno,
                remain,
                a,
                b,
            )
        else:
            raise ValueError("%d > %d ?" % (self.lineno, len(self)))

    @property
    def curinfo(self):
        """Returns line and data set number info."""
        return str(self.lineno) + ":Data set " + str(self.data_set_num)

    @property
    def not_eof(self):
        """Reader is not at the end of file (EOF)."""
        return self.lineno < len(self.lines)

    @property
    def curline(self):
        """Return the current line."""
        try:
            if self.lineno == 0:
                return ""
            else:
                return self.lines[self.lineno - 1]
        except IndexError:
            self.logger.error("%s:Unexpected end of file", self.curinfo)
            raise IndexError("Unexpected end of file")

    def nextline(self, data_set_num=None):
        """Get next line, setting data set number and increment lineno."""
        if data_set_num is not None:
            self.data_set_num = data_set_num
            self.logger.debug("%s:using nextline", self.curinfo)
        self.lineno += 1
        try:
            line = self.lines[self.lineno - 1]
        except IndexError:
            self.lineno -= 1
            self.logger.error("%s:Unexpected end of file", self.curinfo)
            raise IndexError("Unexpected end of file")
        if data_set_num is not None:
            self.logger.debug(
                "%s:returning line with length %d:%r", self.curinfo, len(line), line,
            )
        return line

    def readline(self):
        """Alias for nextline()."""
        return self.nextline()

    def conv(self, item, fmt, name=None):
        """Convert item to format fmt.

        Parameters
        ----------
        item : str
        fmt : str, default ('s')
            's' for string or no conversion (default)
            'i' for integer
            'f' for float
        name : str or None
            Optional name to provide context information for debugging

        """
        try:
            if type(fmt) == np.dtype:
                return fmt.type(item)
            elif fmt == "s":  # string
                return item
            elif fmt == "i":  # integer
                return int(item)
            elif fmt == "f":  # any floating-point number
                # typically either a REAL or DOUBLE PRECISION
                return self.parent._float_type.type(item)
            else:
                raise ValueError(f"Unknown fmt code {fmt!r}")
        except ValueError:
            if name is not None:
                msg = f"Cannot cast {name!r} of {item!r} to type {fmt!r}"
            else:
                msg = f"Cannot cast {item!r} to type {fmt!r}"
            raise ValueError(msg)

    def get_items(self, data_set_num=None, num_items=None, fmt="s", multiline=False):
        """Get items from one or more lines (if multiline) into a list.

        If num_items is defined, then only this count will be returned and any
        remaining items from the line will be ignored. If there are too few
        items on the line, the values will be some form of "zero", such as
        0, 0.0 or ''.

        However, if `multiline=True`, then multiple lines can be read to reach
        num_items.

        If fmt is defined, it must be:
         - 's' for string or no conversion (default)
         - 'i' for integer
         - 'f' for float, as defined by parent._float_type
        """
        if data_set_num is not None:
            self.data_set_num = data_set_num
            self.logger.debug(
                "%s:using get_items for num_items=%s", self.curinfo, num_items,
            )
        startln = self.lineno + 1
        fill_missing = False
        if num_items is None or not multiline:
            items = self.nextline().split()
            if num_items is not None and len(items) > num_items:
                items = items[:num_items]
            if not multiline and num_items is not None and len(items) < num_items:
                fill_missing = num_items - len(items)
        else:
            assert isinstance(num_items, int), type(num_items)
            assert num_items > 0, num_items
            items = []
            while len(items) < num_items:
                items += self.nextline().split()
            if len(items) > num_items:  # trim off too many
                items = items[:num_items]
        if fmt == "s":
            res = items
        else:
            res = [self.conv(x, fmt) for x in items]
        if fill_missing:
            if fmt == "s":
                fill_value = ""
            else:
                fill_value = "0"
            res += [self.conv(fill_value, fmt)] * fill_missing
        if data_set_num is not None:
            if multiline:
                toline = f" to {self.lineno}"
            else:
                toline = ""
            self.logger.debug(
                "%s:read %d items from line %d%s",
                self.data_set_num,
                num_items,
                startln,
                toline,
            )
        return res

    def get_named_items(self, data_set_num, names, fmt="s"):
        """Get items into dict. See get_items for fmt usage."""
        items = self.get_items(data_set_num, len(names), fmt)
        res = {}
        for name, item in zip(names, items):
            if fmt != "s":
                item = self.conv(item, fmt, name)
            res[name] = item
        return res

    def read_named_items(self, data_set_num, names, fmt="s") -> None:
        """Read items into parent. See get_items for fmt usage."""
        startln = self.lineno + 1
        items = self.get_named_items(data_set_num, names, fmt)
        for name in items.keys():
            setattr(self.parent, name, items[name])
        self.logger.debug(
            "%s:read %d items from line %d", self.data_set_num, len(items), startln,
        )

    def read_text(self, data_set_num=0) -> None:
        """Reads 0 or more text (comment) for lines that start with '#'."""
        startln = self.lineno + 1
        self.parent.text = []
        while True:
            try:
                line = self.nextline(data_set_num)
            except IndexError:
                break
            if line.startswith("#"):
                line = line[1:].strip()
                self.parent.text.append(line)
            else:
                self.lineno -= 1  # scroll back one?
                break
        self.logger.debug(
            "%s:read %d lines of text from line %d to %d",
            self.data_set_num,
            len(self.parent.text),
            startln,
            self.lineno,
        )

    def read_options(self, data_set_num, process_aux=True) -> None:
        """Read options, and optionally process auxiliary variables."""
        line = self.nextline(data_set_num)
        self.parent.Options = line.upper().split()
        if hasattr(self.parent, "valid_options"):
            for opt in self.parent.Options:
                if opt not in self.parent.Options:
                    self.logger.warning(
                        "%s:unrecognised option %r", self.data_set_num, opt,
                    )
        if process_aux:
            raise NotImplementedError
        else:
            self.logger.debug(
                "%s:read %d options from line %d:%s",
                self.data_set_num,
                len(self.parent.Options),
                self.lineno,
                self.parent.Options,
            )

    def read_parameter(self, data_set_num, names) -> None:
        """Read [PARAMETER values].

        This optional item must start with the word "PARAMETER". If not found,
        then names are set to 0.

        Parameter names are provided in a list, and are stored as integers
        to the parent object.
        """
        startln = self.lineno + 1
        line = self.nextline(data_set_num)
        self.lineno -= 1
        if line.upper().startswith("PARAMETER"):
            items = self.get_items(num_items=len(names) + 1)
            assert items[0].upper() == "PARAMETER", items[0]
            for name, item in zip(names, items[1:]):
                value = self.conv(item, "i", name)
                setattr(self.parent, name, value)
        else:
            for name in names:
                setattr(self.parent, name, 0)
        self.logger.debug(
            "%s:read %d parameters from line %d", self.data_set_num, len(names), startln,
        )

    def get_array(self, data_set_num, shape, dtype, return_dict=False):
        """Returns array data, similar to array reading utilities U2DREL,
        U2DINT, and U1DREL. If return_dict=True, a dict is returned with all
        other attributes.

        Inputs:
            data_set_num - number
            shape - 1D array, e.g. 10, or 2D array (20, 30)
            dtype - e.g. np.float32 or 'f'

        See Page 8-57 from the MODFLOW-2005 mannual for details.
        """
        startln = self.lineno + 1
        res = {}
        first_line = self.nextline(data_set_num)
        # Comments are considered after a '#' character on the first line
        if "#" in first_line:
            res["text"] = first_line[(first_line.find("#") + 1) :].strip()
        num_type = np.dtype(dtype).type
        res["array"] = ar = np.empty(shape, dtype=dtype)
        num_items = ar.size

        def read_array_data(obj, fmtin):
            """Helper subroutine to actually read array data."""
            fmt = _re_fmtin.search(fmtin.upper())
            if not fmt:
                raise ValueError(f"cannot understand Fortran format: {fmtin!r}")
            fmt = fmt.groupdict()
            if fmt["body"] == "BINARY":
                data_size = ar.size * ar.dtype.itemsize
                if hasattr(obj, "read"):
                    data = obj.read(data_size)
                else:
                    raise NotImplementedError(
                        f"not sure how to 'read' from {obj}",
                    )
                iar = np.frombuffer(data, dtype)
            else:  # ASCII
                items = []
                if not hasattr(obj, "readline"):
                    raise NotImplementedError(
                        f"not sure how to 'readline' from {obj}",
                    )
                if fmt["body"] == "FREE":
                    while len(items) < num_items:
                        items += obj.readline().split()
                else:  # interpret Fortran format
                    if fmt["rep"]:
                        rep = int(fmt["rep"])
                    else:
                        rep = 1
                    width = int(fmt["w"])
                    while len(items) < num_items:
                        line = obj.readline()
                        pos = 0
                        for n in range(rep):
                            try:
                                item = line[pos : pos + width].strip()
                                pos += width
                                if item:
                                    items.append(item)
                            except IndexError:
                                break
                iar = np.fromiter(items, dtype=dtype)
            if iar.size != ar.size:
                raise ValueError(f"expected size {ar.size}, but found {iar.size}")
            return iar

        # First, assume using more modern free-format control line
        control_line = first_line
        dat = control_line.split()
        # First item is the control word
        res["cntrl"] = cntrl = dat[0].upper()
        if cntrl == "CONSTANT":
            # CONSTANT CNSTNT
            if len(dat) < 2:
                raise ValueError("expecting to find at least 2 items for CONSTANT")
            res["cnstnt"] = cnstnt = dat[1]
            if len(dat) > 2 and "text" not in res:
                st = first_line.find(cnstnt) + len(cnstnt)
                res["text"] = first_line[st:].strip()
            ar.fill(cnstnt)
        elif cntrl == "INTERNAL":
            # INTERNAL CNSTNT FMTIN [IPRN]
            if len(dat) < 3:
                raise ValueError("expecting to find at least 3 items for INTERNAL")
            res["cnstnt"] = cnstnt = dat[1]
            res["fmtin"] = fmtin = dat[2]
            if len(dat) >= 4:
                res["iprn"] = iprn = dat[3]  # not used
            if len(dat) > 4 and "text" not in res:
                st = first_line.find(iprn, first_line.find(fmtin)) + len(iprn)
                res["text"] = first_line[st:].strip()
            iar = read_array_data(self, fmtin)
            ar[:] = iar.reshape(shape) * num_type(cnstnt)
        elif cntrl == "EXTERNAL":
            # EXTERNAL Nunit CNSTNT FMTIN IPRN
            if len(dat) < 5:
                raise ValueError("expecting to find at least 5 items for EXTERNAL")
            res["nunit"] = nunit = int(dat[1])
            res["cnstnt"] = cnstnt = dat[2]
            res["fmtin"] = fmtin = dat[3].upper()
            res["iprn"] = iprn = dat[4]  # not used
            if len(dat) > 5 and "text" not in res:
                st = first_line.find(iprn, first_line.find(fmtin)) + len(iprn)
                res["text"] = first_line[st:].strip()
            # Needs a reference to nam[nunit]
            if self.parent.nam is None:
                raise AttributeError("reference to 'nam' required for EXTERNAL array")
            try:
                obj = self.parent.nam[nunit]
            except KeyError:
                raise KeyError("nunit %s not in nam", nunit)
            iar = read_array_data(obj, fmtin)
            ar[:] = iar.reshape(shape) * num_type(cnstnt)
        elif cntrl == "OPEN/CLOSE":
            # OPEN/CLOSE FNAME CNSTNT FMTIN IPRN
            if len(dat) < 5:
                raise ValueError("expecting to find at least 5 items for OPEN/CLOSE")
            res["fname"] = fname = dat[1]
            res["cnstnt"] = cnstnt = dat[2]
            res["fmtin"] = fmtin = dat[3].upper()
            res["iprn"] = iprn = dat[4]
            if len(dat) > 5 and "text" not in res:
                st = first_line.find(iprn, first_line.find(fmtin)) + len(iprn)
                res["text"] = first_line[st:].strip()
            with open(fname, "rb") as fp:
                iar = read_array_data(fp, fmtin)
            ar[:] = iar.reshape(shape) * num_type(cnstnt)
        elif cntrl == "HDF5":
            # GMS extension: http://www.xmswiki.com/xms/GMS:MODFLOW_with_HDF5
            if not h5py:
                raise ImportError("h5py module required to read HDF5 data")
            # HDF5 CNSTNT IPRN "FNAME" "pathInFile" nDim start1 nToRead1 ...
            file_ch = r"\w/\.\-\+_\(\)"
            dat = re.findall("([" + file_ch + ']+|"[' + file_ch + ' ]+")', control_line)
            if len(dat) < 8:
                raise ValueError(
                    "expecting to find at least 8 "
                    "items for HDF5; found " + str(len(dat)),
                )
            assert dat[0].upper() == "HDF5", dat[0]
            res["cnstnt"] = cnstnt = dat[1]
            try:
                cnstnt_val = num_type(cnstnt)
            except ValueError:  # e.g. 1.0 as int 1
                cnstnt_val = num_type(float(cnstnt))
            res["iprn"] = dat[2]
            res["fname"] = fname = dat[3].strip('"')
            res["pathInFile"] = pathInFile = dat[4].strip('"')
            nDim = int(dat[5])
            nDim_len = {1: 8, 2: 10, 3: 12}
            if nDim not in nDim_len:
                raise ValueError(
                    "expecting to nDim to be one of 1, 2, or 3; found " + str(nDim),
                )
            elif len(dat) < nDim_len[nDim]:
                raise ValueError(
                    (
                        "expecting to find at least %d items for HDF5 with "
                        "%d dimensions; found %d"
                    )
                    % (nDim_len[nDim], nDim, len(dat)),
                )
            elif len(dat) > nDim_len[nDim]:
                token = dat[nDim_len[nDim]]
                st = first_line.find(token) + len(token)
                res["text"] = first_line[st:].strip()
            if nDim >= 1:
                start1, nToRead1 = int(dat[6]), int(dat[7])
                slice1 = slice(start1, start1 + nToRead1)
            if nDim >= 2:
                start2, nToRead2 = int(dat[8]), int(dat[9])
                slice2 = slice(start2, start2 + nToRead2)
            if nDim == 3:
                start3, nToRead3 = int(dat[10]), int(dat[11])
                slice3 = slice(start3, start3 + nToRead3)
            fpath = os.path.join(self.parent.nam.ref_dir, fname)
            if not os.path.isfile(fpath):
                raise MissingFile(f"cannot find file '{fpath}'")
            h5 = h5py.File(fpath, "r")
            ds = h5[pathInFile]
            if nDim == 1:
                iar = ds[slice1]
            elif nDim == 2:
                iar = ds[slice1, slice2]
            elif nDim == 3:
                iar = ds[slice1, slice2, slice3]
            h5.close()
            ar[:] = iar.reshape(shape) * cnstnt_val
        elif len(control_line) > 20:  # FIXED-FORMAT CONTROL LINE
            # LOCAT CNSTNT FMTIN IPRN
            del res["cntrl"]  # control word was not used for fixed-format
            try:
                res["locat"] = locat = int(control_line[0:10])
                res["cnstnt"] = cnstnt = control_line[10:20].strip()
                if len(control_line) > 20:
                    res["fmtin"] = fmtin = control_line[20:40].strip().upper()
                if len(control_line) > 40:
                    res["iprn"] = iprn = control_line[40:50].strip()
            except ValueError:
                raise ValueError(
                    f"fixed-format control line not understood: {control_line}",
                )
            if len(control_line) > 50 and "text" not in res:
                res["text"] = first_line[50:].strip()
            if locat == 0:  # all elements are set equal to cnstnt
                ar.fill(cnstnt)
            else:
                nunit = abs(locat)
                if self.parent.nunit == nunit or self.parent.nam is None:
                    obj = self
                else:
                    obj = self.parent.nam[nunit]
                if locat < 0:
                    fmtin = "(BINARY)"
                iar = read_array_data(obj, fmtin)
                ar[:] = iar.reshape(shape) * num_type(cnstnt)
        else:
            raise ValueError(f"array control line not understood: {control_line}")
        if "text" in res:
            withtext = ' with text "' + res["text"] + '"'
        else:
            withtext = ""
        self.logger.debug(
            "%s:read %r array with shape %s from line %d to %d%s",
            self.data_set_num,
            ar.dtype.char,
            ar.shape,
            startln,
            self.lineno,
            withtext,
        )
        if return_dict:
            return res
        else:
            return ar
