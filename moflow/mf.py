# -*- coding: utf-8 -*-
"""
Modflow module
"""

import os
import re
import sys
import inspect
import numpy as np

try:
    import h5py
except ImportError:
    h5py = None

from . import logger, logging


_re_fmtin = re.compile(
    r'\((?P<body>(?P<rep>\d*)(?P<symbol>[IEFG][SN]?)(?P<w>\d+)(\.(?P<d>\d+))?'
    r'|FREE|BINARY)\)')


class MissingFile(Exception):
    pass


class _MFFileReader(object):
    """MODFLOW file reader"""

    def __init__(self, f=None, parent=None):
        """Initialize with parent _MFPackage. File is read from 'f' argument,
        if not None, which is typically a path to a filename, but can also be
        a file reader object with a 'readlines' method, such as BytesIO. If
        'f' is None, then it is obtained from parent.fpath, or parent.fname"""
        if parent is None:
            parent = _MFPackage()
        if not isinstance(parent, _MFPackage):
            raise ValueError("'parent' needs to be a _MFPackage object; found "
                             + str(type(parent)))
        self.parent = parent
        if f is None:
            if getattr(parent, 'fpath', None) is not None:
                f = parent.fpath
            elif getattr(parent, 'fname', None) is not None:
                f = parent.fname
            else:
                raise ValueError('unsure how to open file')
        # Read data
        if hasattr(f, 'readlines'):
            # it is a file reader object, e.g. BytesIO
            self.fname = f.__class__.__name__
            self.lines = f.readlines()
        else:
            self.fpath = self.parent.fpath = f
            if getattr(self, 'fname', None) is None:
                self.fname = os.path.split(self.parent.fpath)[1]
            # Read whole file at once, then close it
            with open(self.parent.fpath, 'r') as fp:
                self.lines = fp.readlines()
        if self.parent.nam is None:
            self.parent.nam = Modflow()
            try:
                self.parent.nam.ref_dir = os.path.dirname(self.fpath)
            except:
                pass
        # Set up logger
        #name = os.path.dirname(f)
        self.logger = logging.getLogger(self.fname)
        self.logger.handlers = logger.handlers
        self.logger.setLevel(logger.level)
        self.logger.info("read file '%s' with %d lines",
                         self.fname, len(self.lines))
        self.lineno = 0
        self.data_set_num = 0

    def __len__(self):
        """Returns number of lines"""
        return len(self.lines)

    def location_exception(self, e):
        """Use to show location of exception while reading file

        Example:
        fp = _MFFileReader(fpath, self)
        try:
            fp.read_text(0)
            ...
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))
        """
        location = '%s:%s:%s:Data set %s:' % \
            (self.parent.__class__.__name__, self.fname, self.lineno,
             self.data_set_num)
        if sys.version_info[0] < 3:
            return "raise type(e), type(e)('" + location + "' + " \
                "str(e)), sys.exc_info()[2]"
        else:
            return "raise type(e)(str(e) + '" + location + "' + " \
                "str(e)).with_traceback(sys.exc_info()[2])"

    def check_end(self):
        """Check end of file and show messages in logger on status"""
        if len(self) == self.lineno:
            self.logger.info("finished reading %d lines", self.lineno)
        elif len(self) > self.lineno:
            remain = len(self) - self.lineno
            a, b = 's', ''
            if remain == 1:
                b, a = a, b
            self.logger.warn(
                "finished reading %d lines, but %d line%s remain%s",
                self.lineno, remain, a, b)
        else:
            raise ValueError("%d > %d ?" % (self.lineno, len(self)))

    @property
    def not_eof(self):
        """Reader is not at the end of file (EOF)"""
        return self.lineno < len(self.lines)

    def next_line(self, data_set_num=None, internal=False):
        """Get next line, setting data set number and increment lineno"""
        self.data_set_num = data_set_num
        line = self.readline()
        if not internal:
            self.logger.debug('%s:read line %d:"%s"',
                              self.data_set_num, self.lineno, line.rstrip())
        return line

    def readline(self):
        """Name of file-like reading method, sort of alias for next_line"""
        self.lineno += 1
        try:
            line = self.lines[self.lineno - 1]
        except IndexError:
            self.lineno -= 1
            raise IndexError('unexpected end of file')
        #if len(line) > 199:
        #    self.logger.warn('%s:%d: line has %d characters',
        #                     self.fname, self.lineno, len(line))
        return line

    def get_named_items(self, data_set_num, names, fmt='s'):
        """Get items into dict. See get_items for fmt usage"""
        items = self.get_items(data_set_num, len(names), fmt, internal=True)
        res = {}
        for name, item in zip(names, items):
            if fmt != 's':
                item = self.conv(item, fmt, name)
            res[name] = item
        return res

    def conv(self, item, fmt, name=None):
        """Helper function to convert item using a format fmt

        The format code must be one of 'i' (integer), 'f' (any floating point),
        or 's' (string). It could also be a numpy dtype."""
        try:
            if type(fmt) == np.dtype:
                return fmt.type(item)
            elif fmt == 's':  # string
                return item
            elif fmt == 'i':  # integer
                return int(item)
            elif fmt == 'f':  # any floating-point number
                # typically either a REAL or DOUBLE PRECISION
                return self.parent._float_type.type(item)
            else:
                raise ValueError('Unknown fmt code %r' % (fmt,))
        except ValueError:
            if name is not None:
                msg = 'Cannot cast %r of %r to type %r' % (name, item, fmt)
            else:
                msg = 'Cannot cast %r to type %r' % (item, fmt)
            raise ValueError(msg)

    def get_items(self, data_set_num=None, num_items=None, fmt='s',
                  multiline=False, internal=False):
        """Get items from one or more (if set) lines into a list. If num_items
        is defined, then only this count will be returned and any remaining
        items from the line will be ignored. If there are too few items on the
        line, the values will be some form of "zero", such as 0, 0.0 or ''.
        However, if `multiline=True`, then multiple lines can be read to reach
        num_items.
        If fmt is defined, it must be:
         - 's' for string or no conversion (default)
         - 'i' for integer
         - 'f' for float, as defined by parent._float_type
         """
        startln = self.lineno + 1
        self.data_set_num = data_set_num
        fill_missing = False
        if num_items is None or not multiline:
            items = self.readline().split()
            if num_items is not None and len(items) > num_items:
                items = items[:num_items]
            if (not multiline and num_items is not None
                    and len(items) < num_items):
                fill_missing = (num_items - len(items))
        else:
            assert isinstance(num_items, int), type(num_items)
            assert num_items > 0, num_items
            items = []
            while len(items) < num_items:
                items += self.readline().split()
            if len(items) > num_items:  # trim off too many
                items = items[:num_items]
        if fmt == 's':
            res = items
        else:
            res = [self.conv(x, fmt) for x in items]
        if fill_missing:
            if fmt == 's':
                fill_value = ''
            else:
                fill_value = '0'
            res += [self.conv(fill_value, fmt)] * fill_missing
        if not internal:
            if multiline:
                toline = ' to %s' % (self.lineno,)
            else:
                toline = ''
            self.logger.debug('%s:read %d items from line %d%s',
                              self.data_set_num, num_items, startln, toline)
        return res

    def read_named_items(self, data_set_num, names, fmt='s'):
        """Read items into parent. See get_items for fmt usage"""
        startln = self.lineno + 1
        items = self.get_named_items(data_set_num, names, fmt)
        for name in items.keys():
            setattr(self.parent, name, items[name])
        self.logger.debug('%s:read %d items from line %d',
                          self.data_set_num, len(items), startln)

    def read_text(self, data_set_num=0):
        """Reads 0 or more text (comment) for lines that start with '#'"""
        startln = self.lineno + 1
        self.parent.text = []
        while True:
            try:
                line = self.next_line(data_set_num, internal=True)
            except IndexError:
                break
            if line.startswith('#'):
                line = line[1:].strip()
                self.parent.text.append(line)
            else:
                self.lineno -= 1  # scroll back one?
                break
        self.logger.debug('%s:read %d lines of text from line %d to %d',
                          self.data_set_num,
                          len(self.parent.text), startln, self.lineno)

    def read_options(self, data_set_num, process_aux=True):
        """Read options, and optionally process auxiliary variables"""
        line = self.next_line(data_set_num, internal=True)
        self.parent.Options = line.upper().split()
        if hasattr(self.parent, 'valid_options'):
            for opt in self.parent.Options:
                if opt not in self.parent.Options:
                    self.logger.warn("%s:unrecognised option %r",
                                     self.data_set_num, opt)
        if process_aux:
            raise NotImplementedError
        else:
            self.logger.debug('%s:read %d options from line %d:%s',
                              self.data_set_num, len(self.parent.Options),
                              self.lineno, self.parent.Options)

    def read_parameter(self, data_set_num, names):
        """Read [PARAMETER values]

        This optional item must start with the word "PARAMETER". If not found,
        then names are set to 0.

        Parameter names are provided in a list, and are stored as integers
        to the parent object.
        """
        startln = self.lineno + 1
        line = self.next_line(data_set_num, internal=True)
        self.lineno -= 1
        if line.upper().startswith('PARAMETER'):
            items = self.get_items(data_set_num, len(names) + 1, internal=True)
            assert items[0].upper() == 'PARAMETER', items[0]
            for name, item in zip(names, items[1:]):
                value = self.conv(item, 'i', name)
                setattr(self.parent, name, value)
        else:
            for name in names:
                setattr(self.parent, name, 0)
        self.logger.debug('%s:read %d parameters from line %d',
                          self.data_set_num, len(names), startln)

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
        first_line = self.next_line(data_set_num, internal=True)
        # Comments are considered after a '#' character on the first line
        if '#' in first_line:
            res['text'] = first_line[(first_line.find('#') + 1):].strip()
        num_type = np.dtype(dtype).type
        res['array'] = ar = np.empty(shape, dtype=dtype)
        num_items = ar.size

        def read_array_data(obj, fmtin):
            '''Helper subroutine to actually read array data'''
            fmt = _re_fmtin.search(fmtin.upper())
            if not fmt:
                raise ValueError(
                    'cannot understand Fortran format: ' + repr(fmtin))
            fmt = fmt.groupdict()
            if fmt['body'] == 'BINARY':
                data_size = ar.size * ar.dtype.itemsize
                if hasattr(obj, 'read'):
                    data = obj.read(data_size)
                else:
                    raise NotImplementedError(
                        "not sure how to 'read' from " + repr(obj))
                iar = np.fromstring(data, dtype)
            else:  # ASCII
                items = []
                if not hasattr(obj, 'readline'):
                    raise NotImplementedError(
                        "not sure how to 'readline' from " + repr(obj))
                if fmt['body'] == 'FREE':
                    while len(items) < num_items:
                        items += obj.readline().split()
                else:  # interpret Fortran format
                    if fmt['rep']:
                        rep = int(fmt['rep'])
                    else:
                        rep = 1
                    width = int(fmt['w'])
                    while len(items) < num_items:
                        line = obj.readline()
                        pos = 0
                        for n in range(rep):
                            try:
                                item = line[pos:pos + width].strip()
                                pos += width
                                if item:
                                    items.append(item)
                            except IndexError:
                                break
                iar = np.fromiter(items, dtype=dtype)
            if iar.size != ar.size:
                raise ValueError('expected size %s, but found %s' %
                                 (ar.size, iar.size))
            return iar

        # First, assume using more modern free-format control line
        control_line = first_line
        dat = control_line.split()
        # First item is the control word
        res['cntrl'] = cntrl = dat[0].upper()
        if cntrl == 'CONSTANT':
            # CONSTANT CNSTNT
            if len(dat) < 2:
                raise ValueError(
                    'expecting to find at least 2 items for CONSTANT')
            res['cnstnt'] = cnstnt = dat[1]
            if len(dat) > 2 and 'text' not in res:
                st = first_line.find(cnstnt) + len(cnstnt)
                res['text'] = first_line[st:].strip()
            ar.fill(cnstnt)
        elif cntrl == 'INTERNAL':
            # INTERNAL CNSTNT FMTIN [IPRN]
            if len(dat) < 3:
                raise ValueError(
                    'expecting to find at least 3 items for INTERNAL')
            res['cnstnt'] = cnstnt = dat[1]
            res['fmtin'] = fmtin = dat[2]
            if len(dat) >= 4:
                res['iprn'] = iprn = dat[3]  # not used
            if len(dat) > 4 and 'text' not in res:
                st = first_line.find(iprn, first_line.find(fmtin)) + len(iprn)
                res['text'] = first_line[st:].strip()
            iar = read_array_data(self, fmtin)
            ar[:] = iar.reshape(shape) * num_type(cnstnt)
        elif cntrl == 'EXTERNAL':
            # EXTERNAL Nunit CNSTNT FMTIN IPRN
            if len(dat) < 5:
                raise ValueError(
                    'expecting to find at least 5 items for EXTERNAL')
            res['nunit'] = nunit = int(dat[1])
            res['cnstnt'] = cnstnt = dat[2]
            res['fmtin'] = fmtin = dat[3].upper()
            res['iprn'] = iprn = dat[4]  # not used
            if len(dat) > 5 and 'text' not in res:
                st = first_line.find(iprn, first_line.find(fmtin)) + len(iprn)
                res['text'] = first_line[st:].strip()
            # Needs a reference to nam[nunit]
            if self.parent.nam is None:
                raise AttributeError(
                    "reference to 'nam' required for EXTERNAL array")
            try:
                obj = self.parent.nam[nunit]
            except KeyError:
                raise KeyError("nunit %s not in nam", nunit)
            iar = read_array_data(obj, fmtin)
            ar[:] = iar.reshape(shape) * num_type(cnstnt)
        elif cntrl == 'OPEN/CLOSE':
            # OPEN/CLOSE FNAME CNSTNT FMTIN IPRN
            if len(dat) < 5:
                raise ValueError(
                    'expecting to find at least 5 items for OPEN/CLOSE')
            res['fname'] = fname = dat[1]
            res['cnstnt'] = cnstnt = dat[2]
            res['fmtin'] = fmtin = dat[3].upper()
            res['iprn'] = iprn = dat[4]
            if len(dat) > 5 and 'text' not in res:
                st = first_line.find(iprn, first_line.find(fmtin)) + len(iprn)
                res['text'] = first_line[st:].strip()
            with open(fname, 'rb') as fp:
                iar = read_array_data(fp, fmtin)
            ar[:] = iar.reshape(shape) * num_type(cnstnt)
        elif cntrl == 'HDF5':
            # GMS extension: http://www.xmswiki.com/xms/GMS:MODFLOW_with_HDF5
            if not h5py:
                raise ImportError('h5py module required to read HDF5 data')
            # HDF5 CNSTNT IPRN "FNAME" "pathInFile" nDim start1 nToRead1 ...
            file_ch = r'\w/\.\-\+_\(\)'
            dat = re.findall('([' + file_ch + ']+|"[' + file_ch + ' ]+")',
                             control_line)
            if len(dat) < 8:
                raise ValueError('expecting to find at least 8 '
                                 'items for HDF5; found ' + str(len(dat)))
            assert dat[0].upper() == 'HDF5', dat[0]
            res['cnstnt'] = cnstnt = dat[1]
            try:
                cnstnt_val = num_type(cnstnt)
            except ValueError:  # e.g. 1.0 as int 1
                cnstnt_val = num_type(float(cnstnt))
            res['iprn'] = dat[2]
            res['fname'] = fname = dat[3].strip('"')
            res['pathInFile'] = pathInFile = dat[4].strip('"')
            nDim = int(dat[5])
            nDim_len = {1: 8, 2: 10, 3: 12}
            if nDim not in nDim_len:
                raise ValueError('expecting to nDim to be one of 1, 2, or 3; '
                                 'found ' + str(nDim))
            elif len(dat) < nDim_len[nDim]:
                raise ValueError(
                    ('expecting to find at least %d items for HDF5 with '
                     '%d dimensions; found %d') %
                    (nDim_len[nDim], nDim, len(dat)))
            elif len(dat) > nDim_len[nDim]:
                token = dat[nDim_len[nDim]]
                st = first_line.find(token) + len(token)
                res['text'] = first_line[st:].strip()
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
                raise MissingFile("cannot find file '%s'" % (fpath,))
            h5 = h5py.File(fpath, 'r')
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
            del res['cntrl']  # control word was not used for fixed-format
            try:
                res['locat'] = locat = int(control_line[0:10])
                res['cnstnt'] = cnstnt = control_line[10:20].strip()
                if len(control_line) > 20:
                    res['fmtin'] = fmtin = control_line[20:40].strip().upper()
                if len(control_line) > 40:
                    res['iprn'] = iprn = control_line[40:50].strip()
            except ValueError:
                raise ValueError('fixed-format control line not '
                                 'understood: ' + repr(control_line))
            if len(control_line) > 50 and 'text' not in res:
                res['text'] = first_line[50:].strip()
            if locat == 0:  # all elements are set equal to cnstnt
                ar.fill(cnstnt)
            else:
                nunit = abs(locat)
                if self.parent.nunit == nunit:
                    obj = self
                elif self.parent.nam is None:
                    obj = self
                else:
                    obj = self.parent.nam[nunit]
                if locat < 0:
                    fmtin = '(BINARY)'
                iar = read_array_data(obj, fmtin)
                ar[:] = iar.reshape(shape) * num_type(cnstnt)
        else:
            raise ValueError('array control line not understood: ' +
                             repr(control_line))
        if 'text' in res:
            withtext = ' with text "' + res['text'] + '"'
        else:
            withtext = ''
        self.logger.debug(
            '%s:read %r array with shape %s from line %d to %d%s',
            self.data_set_num, ar.dtype.char, ar.shape,
            startln, self.lineno, withtext)
        if return_dict:
            return res
        else:
            return ar


class _MFPackage(object):
    """The inherited ___class__.__name__ is the name of the package, which
    is always upper case and may have a version number following"""

    _float_type = np.dtype('f')  # REAL
    text = None

    @property
    def _attr_name(self):
        """It is assumed Modflow properties to be the lower-case name of Ftype,
        or the class name"""
        return self.__class__.__name__.lower()

    @property
    def _default_fname(self):
        """Generate default filename"""
        if self.nam is None:
            raise AttributeError("'nam' not set to a Modflow object")
        prefix = self.nam.prefix
        if prefix is None:
            raise ValueError("'nam.prefix' is not set")
        return prefix + '.' + self._attr_name

    @property
    def nam(self):
        """Returns back-reference to nam or Modflow object"""
        return getattr(self, '_nam', None)

    @nam.setter
    def nam(self, value):
        if value is not None and not isinstance(value, Modflow):
            raise ValueError("'nam' needs to be a Modflow object; found "
                             + str(type(value)))
        setattr(self, '_nam', value)

    @property
    def nunit(self):
        """Nunit is the Fortran unit to be used when reading from or writing
        to the file. Any legal unit number on the computer being used can
        be specified except units 96-99. Unspecified is unit 0."""
        return getattr(self, '_nunit', 0)

    @nunit.setter
    def nunit(self, value):
        if value is None:
            value = 0
        else:
            try:
                value = int(value)
            except ValueError:
                self._logger.error("nunit: %r is not an integer", value)
        if value >= 96 and value <= 99:
            self._logger.error("nunit: %r is not valid", value)
        setattr(self, '_nunit', value)

    @property
    def fname(self):
        """Fname is the name of the file, which is a character value.
        Pathnames may be specified as part of fname. However, space characters
        are not allowed in fname. Note that this variable may not be a valid
        path to a file for all operating systems, use 'fpath' for this."""
        return getattr(self, '_fname', None)

    @fname.setter
    def fname(self, value):
        if value is not None:
            if ' ' in value:
                self._logger.warn("fname: %d space characters found in %r",
                                  value.count(' '), value)
        self._fname = value

    @property
    def fpath(self):
        """A valid path to an existing file that can be read, or has been
        written. It has precidence over 'fname' for reading."""
        return getattr(self, '_fpath', None)

    @fpath.setter
    def fpath(self, value):
        if value is not None:
            try:
                assert os.path.isfile(value)
            except:
                raise MissingFile(
                    "'%s' is not a valid path to a file" % (value,))
        self._fpath = value

    @property
    def nam_option(self):
        """Returns 'option' for Name File, which can be: OLD, REPLACE, UNKNOWN
        """
        return getattr(self, '_nam_option', None)

    @nam_option.setter
    def nam_option(self, value):
        if hasattr(value, 'upper') and value.upper() != value:
            self._logger.info('nam_option: changing value from %r to %r',
                              value, value.upper())
            value = value.upper()
        expected = [None, 'OLD', 'REPLACE', 'UNKNOWN']
        if value not in expected:
            self._logger.error("nam_option: %r is not valid; expecting one of "
                               "%r", value, expected)
        self._nam_option = value

    def __init__(self, fpath=None, *args, **kwargs):
        """Package constructor"""
        # Set up logger
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.handlers = logger.handlers
        self._logger.setLevel(logger.level)
        if args:
            self._logger.warn('unused args: %r', args)
        if 'dis' in kwargs:
            self.dis = kwargs.pop('dis')
        elif 'disu' in kwargs:
            self.disu = kwargs.pop('disu')
        if fpath is not None:
            self.fpath = fpath
            self.read()
        for kw in kwargs.keys():
            if hasattr(self, kw):
                setattr(self, kw, kwargs.pop(kw))
        if kwargs:
            self._logger.warn('unused kwargs: %r', kwargs)

    def __repr__(self):
        """Returns string representation"""
        return '<' + self.__class__.__name__ + '>'

    def read(self, *args, **kwargs):
        raise NotImplementedError("'read' not implemented for " +
                                  repr(self.__class__.__name__))

    def write(self, *args, **kwargs):
        raise NotImplementedError("'write' not implemented for " +
                                  repr(self.__class__.__name__))

    def _setup_read(self):
        """Hook to set-up attributes"""
        pass


class _MFPackageDIS(_MFPackage):
    """Abstract class for packages that use data from either DIS or DISU"""
    _dis = None
    _disu = None

    @property
    def dis(self):
        """Reference to DIS - Discretization Package"""
        return self._dis

    @dis.setter
    def dis(self, dis):
        if not (dis is None or isinstance(dis, DIS)):
            raise TypeError('dis is not type DIS; found ' + repr(type(dis)))
        elif dis and self.disu:
            raise TypeError("reference to 'disu' established; cannot also "
                            "attach 'dis'")
        self._dis = dis
        stress_period = getattr(self, 'stress_period', None)
        if stress_period is not None:
            if dis.nper != stress_period:
                self._logger.error('stress periods from dis.nper (%s) do not '
                                   'match those established in this package '
                                   '(%s)', dis.nper, stress_period)
    @property
    def disu(self):
        """Reference to DISU - Unstructured Discretization Package"""
        return self._disu

    @disu.setter
    def disu(self, disu):
        if not (disu is None or isinstance(disu, DISU)):
            raise TypeError('disu is not type DISU; found ' + repr(type(disu)))
        elif disu and self.dis:
            raise TypeError("reference to 'dis' established; cannot also "
                            "attach 'disu'")
        self._disu = disu
        stress_period = getattr(self, 'stress_period', None)
        if stress_period is not None:
            if disu.nper != stress_period:
                self._logger.error('stress periods from disu.nper (%s) do not '
                                   'match those established in this package '
                                   '(%s)', disu.nper, stress_period)

    @property
    def nper(self):
        """Number of stress periods in the simulation"""
        return self._dis and self._dis.nper or self._disu and self._disu.nper

    def _setup_read(self):
        """Hook to set-up and check attributes"""
        _MFPackage._setup_read(self)
        if self.dis is None and self.disu is None:
            raise AttributeError("'dis' or 'disu' is not set")


class _DIS(_MFPackage):
    """Abstract discretization file"""

    @property
    def nlay(self):
        """Number of layers in the model grid"""
        return getattr(self, '_nlay', None)

    @nlay.setter
    def nlay(self, value):
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError("invalid 'nlay': " + repr(value))
        setattr(self, '_nlay', value)

    @property
    def nper(self):
        """Number of stress periods in the simulation"""
        return getattr(self, '_nper', None)

    @nper.setter
    def nper(self, value):
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError("invalid 'nper': " + repr(value))
        setattr(self, '_nper', value)

    @property
    def itmuni(self):
        """Time unit of model data, which must be consistent for all data
        values that involve time."""
        return getattr(self, '_itmuni', 0)

    @itmuni.setter
    def itmuni(self, value):
        if value is not None:
            try:
                assert int(value) is not None
            except:
                raise ValueError("invalid 'itmuni': " + repr(value))
        setattr(self, '_itmuni', value)

    _itmuni_str = {0: '?', 1: 's', 2: 'min', 3: 'h', 4: 'd', 5: 'y'}
    _str_itmuni = {v: k for k, v in _itmuni_str.items()}

    @property
    def itmuni_str(self):
        """Time unit character(s) from ITMUNI.
            (0) ? - undefined
            (1) s - seconds
            (2) min - minutes
            (3) h - hours
            (4) d - days
            (5) y - years"""
        try:
            return self._itmuni_str[self.itmuni]
        except KeyError:
            raise ValueError("invalid 'itmuni': " + repr(self.itmuni))

    @itmuni_str.setter
    def itmuni_str(self, value):
        """Set time unit ITMUNI; no other dat is modified."""
        d = dict((v, k) for k, v in self._str_itmuni.iteritems())
        try:
            self.itmuni = d[value]
        except KeyError:
            raise ValueError("invalid 'itmuni_str': " + repr(value))

    @property
    def lenuni(self):
        """Length unit of model data, which must be consistent for all data
        values that involve length."""
        return getattr(self, '_lenuni', 0)

    @lenuni.setter
    def lenuni(self, value):
        if value is not None:
            try:
                assert int(value) is not None
            except:
                raise ValueError("invalid 'lenuni': " + repr(value))
        setattr(self, '_lenuni', value)

    _lenuni_str = {0: '?', 1: 'ft', 2: 'm', 3: 'cm'}
    _str_lenuni = {v: k for k, v in _lenuni_str.items()}

    @property
    def lenuni_str(self):
        """Length unit character(s) from lenuni.
            (0) ?  - undefined
            (1) ft - feet
            (2) m  - meters
            (3) cm - centimeters"""
        try:
            return self._lenuni_str[self.lenuni]
        except KeyError:
            raise ValueError("invalid 'lenuni': " + repr(self.lenuni))

    @lenuni_str.setter
    def lenuni_str(self, value):
        try:
            self.lenuni = self._str_lenuni[value]
        except KeyError:
            raise ValueError("invalid 'lenuni_str': " + repr(value))

    def _read_stress_period_data(self, fp, data_set_num):
        startln = fp.lineno + 1
        # PERLEN NSTP TSMULT Ss/tr
        stress_period_dtype = np.dtype([
            ('perlen', self._float_type),
            ('nstp', 'i'),
            ('tsmult', self._float_type),
            ('sstr', '|S2'),
        ])
        self.stress_period = np.zeros(self.nper, dtype=stress_period_dtype)
        names = self.stress_period.dtype.names
        for row in self.stress_period:
            dat = fp.get_named_items(data_set_num, names)
            for name in names:
                row[name] = dat[name]
        for name in names:
            setattr(self, name, self.stress_period[name])
        fp.logger.debug('%s:read %d stress period%s from line %d to %d',
                        fp.data_set_num, len(self.stress_period),
                        '' if len(self.stress_period) == 1 else 's',
                        startln, fp.lineno)


class DIS(_DIS):
    """Discretization file"""

    @property
    def nrow(self):
        """Number of rows in the model grid"""
        return getattr(self, '_nrow', None)

    @nrow.setter
    def nrow(self, value):
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError("invalid 'nrow': " + repr(value))
        setattr(self, '_nrow', value)

    @property
    def ncol(self):
        """Number of columns in the model grid"""
        return getattr(self, '_ncol', None)

    @ncol.setter
    def ncol(self, value):
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError("invalid 'ncol': " + repr(value))
        setattr(self, '_ncol', value)

    @property
    def shape2d(self):
        """Array shape in 2D: (nrow, ncol)"""
        return (self.nrow, self.ncol)

    @property
    def shape3d(self):
        """Array shape in 3D: (nlay, nrow, ncol)"""
        return (self.nlay, self.nrow, self.ncol)

    @property
    def shape4d(self):
        """Array shape in 4D: (nper, nlay, nrow, ncol)"""
        return (self.nper, self.nlay, self.nrow, self.ncol)

    @property
    def Area(self):
        """Returns 2D array of grid areas"""
        rows = self.delr.astype('d').reshape((1,) + self.delr.shape)
        cols = self.delc.astype('d').reshape(self.delc.shape + (1,))
        return rows * cols

    @property
    def Volume(self):
        """Returns 3D array of grid volumes"""
        elevs = np.vstack((self.Top.astype('d').reshape((1,) + self.Top.shape),
                           self.BOTM.astype('d')))
        heights = -np.diff(elevs, axis=0)
        area = self.area
        area.shape = (1,) + area.shape
        return area * heights

    @property
    def top_left(self):
        """Top left coordinate pair (X, Y) for corner of grid"""
        value = getattr(self, '_top_left', None)
        if value is None:
            self._top_left = value = (0.0, 0.0)
            self._logger.warn("'top_left' is not set; using %s", value)
        return value

    @top_left.setter
    def top_left(self, value):
        if value is not None:
            try:
                assert len(value) == 2
            except:
                raise ValueError("invalid 'top_left': must be a tuple pair "
                                 "(X, Y); found: " + repr(value))
        self._top_left = value

    @property
    def geotransform(self):
        """Get GeoTransform for exporting rasters with GDAL

        Requires self.top_left_X and self.top_left_Y to be set,
        as MODFLOW grids are locally defined from (0, 0).

        Returns a six-item tuple of the format:
            [0] top left x
            [1] w-e pixel resolution
            [2] rotation, 0 if image is "north up"
            [3] top left y
            [4] rotation, 0 if image is "north up"
            [5] n-s pixel resolution
        for example: (2779000.0, 100.0, 0.0, 6164500.0, 0.0, -100.0)
        """
        # Determine GeoTransform
        dx = self.delc.mean()
        if self.delc.min() != self.delc.max():
            self._logger.warn(
                "'delc' values range from %s to %s; using mean of %s",
                self.delc.min(), self.delc.max(), dx)
        dy = self.delr.mean()
        if self.delr.min() != self.delr.max():
            self._logger.warn(
                "'delr' values range from %s to %s; using mean of %s",
                self.delr.min(), self.delr.max(), dy)
        top_left_X, top_left_Y = self.top_left
        return (top_left_X,  # top left x
                dx, 0.0,  # w-e pixel resolution; rotation
                top_left_Y,  # top left y
                0.0, -dy)  # rotation, n-s pixel resolution

    def __repr__(self):
        return '<%s: nper=%s, nlay=%s, nrow=%s, ncol=%s>' %\
            (self.__class__.__name__, self.nper, self.nlay, self.nrow,
             self.ncol)

    def read(self, fpath=None):
        """Read DIS file"""
        fp = _MFFileReader(fpath, self)
        try:
            # 0: [#Text]
            fp.read_text(0)
            # 1: NLAY NROW NCOL NPER ITMUNI LENUNI
            fp.read_named_items(1, ['nlay', 'nrow', 'ncol', 'nper',
                                    'itmuni', 'lenuni'], 'i')
            # 2: LAYCBD(NLAY)
            dat = fp.get_items(2, num_items=self.nlay, multiline=True)
            self.laycbd = [int(x) for x in dat]
            if self.nlay > 1 and self.laycbd[-1]:
                self._logger.error("%d:%d:LAYCBD for the bottom layer must be "
                                   "'0'; found %r", fp.data_set_num, fp.lineno,
                                   dat[-1])
            # 3: DELR(NCOL) - U1DREL
            self.delr = fp.get_array(3, self.ncol, self._float_type)
            # 4: DELC(NROW) - U1DREL
            self.delc = fp.get_array(4, self.nrow, self._float_type)
            # 5: Top(NCOL,NROW) - U2DREL
            self.top = fp.get_array(5, self.shape2d, self._float_type)
            # 6: BOTM(NCOL,NROW) - U2DREL
            ## for each model layer and Quasi-3D confining bed
            num_botm = self.nlay
            if self.nlay > 1:
                num_botm += sum(self.laycbd)
            self.botm = np.empty((num_botm,) + self.shape2d, self._float_type)
            for ibot in range(num_botm):
                n = '6:L' + str(ibot + 1)
                self.botm[ibot, :, :] = \
                    fp.get_array(n, self.shape2d, self._float_type)
            ## FOR EACH STRESS PERIOD
            # 7: PERLEN NSTP TSMULT Ss/tr
            self._read_stress_period_data(fp, 7)
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))


class DISU(_DIS):
    """Unstructured Discretization file"""

    @property
    def nodes(self):
        """Number of nodes in the model grid"""
        return getattr(self, '_nodes', None)

    @nodes.setter
    def nodes(self, value):
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError("invalid 'nodes': " + repr(value))
        setattr(self, '_nodes', value)

    @property
    def njag(self):
        """Total number of connections of an unstructured grid"""
        return getattr(self, '_njag', None)

    @njag.setter
    def njag(self, value):
        if value is not None:
            try:
                value = int(value)
                assert value > 0
            except:
                raise ValueError("invalid 'njag': " + repr(value))
        setattr(self, '_njag', value)

    @property
    def njags(self):
        """Total number of non-zero entries for symmetric input of symmetric
        flow properties between cells; njags = (njag - nodes)/2"""
        if ((self.njag - self.nodes) % 2) != 0:
            self._logger.warn("'njags' determined from odd values")
        return int((self.njag - self.nodes) / 2)

    @property
    def ivsd(self):
        """Vertical sub-discretization index, either 0, 1, or -1.
            *  0: no sub-discretization of layers within the model domain
            *  1: there could be vertical sub-discretization of layers
            * -1: no vertical sub-discretization of layers, and horizontal
                discretization of all layers is the same
        """
        return getattr(self, '_ivsd', None)

    @ivsd.setter
    def ivsd(self, value):
        if value not in (None, 0, 1, -1):
            raise ValueError("invalid 'ivsd: must be 0, 1, or -1")
        setattr(self, '_ivsd', value)

    @property
    def idsymrd(self):
        """Flag indicating if the finite-volume connectivity, either 0, or 1.
            * 0: finite-volume connectivity information is provided for the
                full matrix of the porous matrix grid-block connections of an
                unstructured grid
            * 1: finite-volume connectivity information is provided only for
                the upper triangular portion of the porous matrix grid-block
                connections within the unstructured grid
        """
        return getattr(self, '_idsymrd', None)

    @idsymrd.setter
    def idsymrd(self, value):
        if value not in (None, 0, 1):
            raise ValueError("invalid 'idsymrd: must be 0, or 1")
        setattr(self, '_idsymrd', value)

    def __repr__(self):
        return '<%s: nper=%s, nlay=%s, nodes=%s, njag=%s, ivsd=%s>' %\
            (self.__class__.__name__, self.nper, self.nlay, self.nodes,
             self.njag, self.ivsd)

    def read(self, fpath=None):
        """Read DISU file"""
        fp = _MFFileReader(fpath, self)
        try:
            # 0: [#Text]
            fp.read_text(0)
            # 1: NODES NLAY NJAG IVSD NPER ITMUNI LENUNI IDSYMRD
            fp.read_named_items(1, ['nodes', 'nlay', 'njag', 'ivsd', 'nper',
                                    'itmuni', 'lenuni', 'idsymrd'], 'i')
            # 2: LAYCBD(NLAY)
            dat = fp.get_items(2, num_items=self.nlay, multiline=True)
            self.laycbd = [int(x) for x in dat]
            if self.nlay > 1 and self.laycbd[-1]:
                self._logger.error("%d: LAYCBD for the bottom layer must be 0;"
                                   ' found %s', fp.lineno, dat[-1])
            # 3: NODELAY(NLAY) - U1DINT
            self.Nodelay = fp.get_array(3, self.nlay, 'i')
            # 4: Top(NDSLAY) - U1DREL
            self.Top = []
            for ilay, ndslay in enumerate(self.Nodelay):
                n = '4:L' + str(ilay + 1)
                self.Top.append(fp.get_array(n, ndslay, self._float_type))
            # 5: Bot(NDSLAY) - U1DREL
            self.Bot = []
            for ilay, ndslay in enumerate(self.Nodelay):
                n = '5:L' + str(ilay + 1)
                self.Bot.append(fp.get_array(n, ndslay, self._float_type))
            # 6: Area(NDSLAY) - U1DREL
            if self.ivsd == -1:
                self.Area = fp.get_array(6, self.Nodelay[0], self._float_type)
            else:
                self.Area = []
                for ilay, ndslay in enumerate(self.Nodelay):
                    n = '6:L' + str(ilay + 1)
                    self.Area.append(fp.get_array(n, ndslay, self._float_type))
            # 7: IAC(NODES) - U1DINT
            self.Iac = fp.get_array(7, self.nodes, 'i')
            # 8: JA(NJAG) - U1DINT
            self.Ja = fp.get_array(8, self.njag, 'i')
            if self.ivsd == 1:
                # 9: IVC(NJAG) - U1DINT
                self.Ivc = fp.get_array(9, self.njag, 'i')
            else:
                fp.logger.debug('9:skipped; ivsd=%s', self.ivsd)
            if self.idsymrd == 1:
                # 10a: CL1(NJAG) - U1DREL
                self.Cl1 = fp.get_array('10a', self.njags, self._float_type)
                # 10b: CL2(NJAG) - U1DREL
                self.Cl2 = fp.get_array('10b', self.njags, self._float_type)
                fp.logger.debug('11:skipped; idsymrd=%s', self.idsymrd)
            elif self.idsymrd == 0:
                fp.logger.debug('10:skipped; idsymrd=%s', self.idsymrd)
                # 11: CL12(NJAG) - U1DREL
                self.Cl12 = fp.get_array(11, self.njag, self._float_type)
            else:
                fp.logger.debug('10 to 11:skipped; idsymrd=%s', self.idsymrd)
            # 12: FAHL(NJAG/NJAGS) - U1DREL
            self.Fahl = fp.get_array(12, self.njag, self._float_type)

            # FOR EACH STRESS PERIOD
            # 13: PERLEN NSTP TSMULT Ss/Tr
            self._read_stress_period_data(fp, 13)
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))


class MULT(_MFPackage):
    """Multiplier array file"""


class ZONE(_MFPackage):
    """Zone array"""


class PVAL(_MFPackage):
    """Parameter Value file"""


class BAS6(_MFPackageDIS):
    """Ground-Water Flow Process Basic Package"""

    valid_options = ['XSECTION', 'CHTOCH', 'FREE', 'PRINTTIME',
                     'SHOWPROGRESS', 'STOPERROR']

    _Options = []

    @property
    def Options(self):
        """List of Options"""
        return getattr(self, '_Options')

    @Options.setter
    def Options(self, value):
        setattr(self, '_Options', value)

    @property
    def free(self):
        """Indicates that free format is used for input variables throughout
        the Basic Package and other packages as indicated in their input
        instructions."""
        w = 'FREE'
        return any([k in self.Options for k in [w, w.lower(), w.upper()]])

    @free.setter
    def free(self, value):
        cur = self.free
        w = 'FREE'
        if value and not cur:
            self.Options.append(w)
        elif not value and cur:
            for k in [w, w.lower(), w.upper()]:
                if k in self.Options:
                    self.Options.remove(k)

    @property
    def xsection(self):
        """Indicates that the model is a 1-row cross section for which STRT
        and IBOUND should each be read as single two-dimensional variables
        with dimensions of NCOL and NLAY."""
        w = 'XSECTION'
        return any([k in self.Options for k in [w, w.lower(), w.upper()]])

    @xsection.setter
    def xsection(self, value):
        cur = self.free
        w = 'XSECTION'
        if value and not cur:
            self.Options.append(w)
        elif not value and cur:
            for k in [w, w.lower(), w.upper()]:
                if k in self.Options:
                    self.Options.remove(k)

    @property
    def Ibound(self):
        """The boundary variable array, which is < 0 for constant heads,
        = 0 for inactive cells and > 0 for active cells."""
        return getattr(self, '_Ibound', None)

    @Ibound.setter
    def Ibound(self, value):
        setattr(self, '_Ibound', value)

    @property
    def hnoflo(self):
        """The value of head to be assigned to all inactive (no flow) cells
        (ibound == 0) throughout the simulation."""
        return getattr(self, '_hnoflo', None)

    @hnoflo.setter
    def hnoflo(self, value):
        setattr(self, '_hnoflo', value)

    @property
    def Strt(self):
        """Initial or starting head array."""
        return getattr(self, '_Strt', None)

    @Strt.setter
    def Strt(self, value):
        setattr(self, '_Strt', value)

    def read(self, fpath=None):
        """Read BAS6 file"""
        self._setup_read()
        fp = _MFFileReader(fpath, self)
        try:
            # 0: [#Text]
            fp.read_text(0)
            # 1: Options
            fp.read_options(1, False)
            if self.disu:
                # 2a. IBOUND(NDSLAY) -- U1DINT
                self.Ibound = []
                if not self.xsection:
                    for ilay, ndslay in enumerate(self.disu.Nodelay):
                        n = '2a:L' + str(ilay + 1)
                        self.Ibound.append(
                            fp.get_array(n, ndslay, self._float_type))
                else:  # same???
                    for ilay, ndslay in enumerate(self.disu.Nodelay):
                        n = '2a:L' + str(ilay + 1)
                        self.Ibound.append(
                            fp.get_array(n, ndslay, self._float_type))
            else:
                # 2b: IBOUND(NCOL,NROW) or (NCOL,NLAY) -- U2DINT
                if self.xsection:
                    assert self.dis.nrow == 1, self.dis.nrow
                    LC_shape = (self.dis.nlay, self.dis.ncol)
                    self.Ibound = fp.get_array('2b', LC_shape, 'i')
                else:
                    self.Ibound = np.empty(self.dis.shape3d, 'i')
                    for ilay in range(self.dis.nlay):
                        n = '2b:L' + str(ilay + 1)
                        self.Ibound[ilay, :, :] = \
                            fp.get_array(n, self.dis.shape2d, 'i')
            # 3: HNOFLO (10-character field unless Item 1 contains 'FREE'.)
            line = fp.next_line(3)
            if self.free:
                self.hnoflo = self._float_type.type(line.split()[0])
            else:
                self.hnoflo = self._float_type.type(line[0:10])
            # 4: STRT(NCOL,NROW) or (NCOL,NLAY) -- U2DREL
            if self.xsection:
                self.strt = fp.get_array(4, LC_shape, self._float_type)
            else:
                self.strt = np.empty(self.dis.shape3d, self._float_type)
                for ilay in range(self.dis.nlay):
                    self.strt[ilay, :, :] = \
                        fp.get_array(4, self.dis.shape2d, self._float_type)
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))


class OC(_MFPackage):
    """Ground-Water Flow Process Output Control Option"""


class BCF6(_MFPackage):
    """Ground-Water Flow Process Block-Centered Flow Package"""


class LPF(_MFPackage):
    """Ground-Water Flow Process Layer Property Flow Package"""


class HUF2(_MFPackage):
    """Hydrogeologic Unit Flow Package"""


class UPW(_MFPackage):
    """Upstream Weighting Package (MODFLOW-NWT only)"""


class SWT(_MFPackage):
    """Subsidence and Aquifer-System Compaction Package for Water-Table
    Aquifers"""


class HFB6(_MFPackage):
    """Ground-Water Flow Process Horizontal Flow Barrier Package"""


class UZF(_MFPackage):
    """Ground-Water Flow Process Unsaturated-Zone Flow Package"""


class RCH(_MFPackageDIS):
    """Recharge Package"""

    @property
    def nrchop(self):
        """Recharge option code of either 1, 2 or 3.
            * 1: Recharge is only to the top grid layer.
            * 2: Vertical distribution of recharge is specified in layer
                 variable IRCH.
            * 3: Recharge is applied to the highest active cell in each
                 vertical column. A constant-head node intercepts recharge and
                 prevents deeper infiltration.
        """
        return getattr(self, '_nrchop', None)

    @nrchop.setter
    def nrchop(self, value):
        if value not in (None, 1, 2, 3):
            raise ValueError("invalid 'nrchop: must be 1, 2, or 3")
        setattr(self, '_nrchop', value)

    @property
    def irchcb(self):
        """Flag and a unit number for writing cell-by-cell flow terms."""
        return getattr(self, '_irchcb', None)

    @irchcb.setter
    def irchcb(self, value):
        setattr(self, '_irchcb', value)

    @property
    def Rech(self):
        """Recharge flux array with dimensions (nper, nrow, ncol)."""
        return getattr(self, '_Rech', None)

    @Rech.setter
    def Rech(self, value):
        setattr(self, '_Rech', value)

    @property
    def Irch(self):
        """Layer number variable that defines the layer in each vertical
        column where recharge is applied."""
        return getattr(self, '_Irch', None)

    @Irch.setter
    def Irch(self, value):
        if value is not None and self.nrchop != 2:
            self._logger.error("'nrchop' must be 2")
        setattr(self, '_Irch', value)

    def read(self, fpath=None):
        """Read RCH file"""
        raise NotImplementedError
        self._setup_read()
        fp = _MFFileReader(fpath, self)
        try:
            # 0: [#Text]
            fp.read_text(0)
            # 1: [ PARAMETER NPRCH]
            fp.read_parameter(1, ['nprch'])
            # 2: NRCHOP IRCHCB
            fp.read_named_items(2, ['nrchop', 'irchcb'], fmt='i')
            if self.disu:
                # 2b. MXNDRCH
                fp.read_named_items(2, ['mxndrch'], fmt='i')
            ## Repeat Items 3 and 4 for each parameter; NPRCH times
            for ipar in range(self.nprch):
                # 3: [PARNAM PARTYP Parval NCLU [INSTANCES NUMINST]]
                # 4a: [INSTNAM]
                # 4b: [Mltarr Zonarr IZ]
                raise NotImplementedError('PARAMETER not suported')
            if self.dis:
                top_shape = (self.dis.nper, self.dis.nrow, self.dis.ncol)
                shape2d = self.dis.shape2d
                self.Rech = np.empty(top_shape, self._float_type)
                if self.nrchop == 2:
                    self.Irch = np.empty(top_shape, 'i')
                else:
                    self.Irch = None

            ## FOR EACH STRESS PERIOD
            stress_period = 0
            for sp in range(self.nper):
                stress_period += 1
                # 5: INRECH [INIRCH]
                if self.nrchop == 2:
                    inrech, inirch = fp.get_items(5, 2, fmt='i')
                else:
                    inrech = fp.get_items(5, 1, fmt='i')[0]
                    inirch = 0
                if inrech < 0 and sp == 0:
                    raise ValueError(
                        "INRECH specified to read results from previous "
                        "stress period, but this is the first stress period")
                # Either Item 6 or Item 7 may be read, but not both
                if self.nprch == 0 and inrech >= 0:
                    # 6: [RECH(NCOL,NROW)]
                    self.Rech[sp] = fp.get_array(6, shape2d, self._float_type)
                elif self.nprch > 0 and inrech > 0:
                    # 7: [Pname [Iname] [IRCHPF]]
                    raise NotImplementedError('PARAMETER not suported')
                elif inrech < 0:
                    # recharge rates from the preceding stress period are used
                    self.Rech[sp] = self.Rech[sp - 1]
                else:
                    raise ValueError("undefined logic for Data Set 6 or 7")
                if self.nrchop == 2 and inirch >= 0:
                    # 8: [IRCH(NCOL,NROW)]
                    self.Irch[sp] = fp.get_array(8, shape2d, 'i')
            fp.check_end()
        except Exception as e:
            exec(fp.location_exception(e))


class RIV(_MFPackage):
    """Ground-Water Flow Process River Package"""


class WEL(_MFPackage):
    """Ground-Water Flow Process Well Package"""


class DRN(_MFPackage):
    """Ground-Water Flow Process Drain Package"""


class GHB(_MFPackage):
    """Ground-Water Flow Process General-Head Boundary Package"""


class EVT(_MFPackage):
    """Ground-Water Flow Process Evapotranspiration Package"""


class BFH(_MFPackage):
    """BFH - Boundary Flow and Head Package"""


class CHD(_MFPackage):
    """Ground-Water Flow Process Time-Variant Specified-Head Package"""


class SIP(_MFPackage):
    """Strongly Implicit Procedure Package"""


class SOR(_MFPackage):
    """Slice-Successive Over-Relaxation Package"""


class PCG(_MFPackage):
    """Preconditioned Conjugate-Gradient Package"""


class DE4(_MFPackage):
    """Direct Solution Package"""


class GMG(_MFPackage):
    """GMG - Geometric Multigrid Solver"""


class LMG(_MFPackage):
    """Link-AMG Package"""


class SMS(_MFPackage):
    """Sparse Matrix Solver"""


class CLN(_MFPackage):
    """Connected Linear Network Process"""


class GNC(_MFPackage):
    """Ghost Node Correction Package"""


class IBS(_MFPackage):
    """Interbed-Storage Package"""


class NWT(_MFPackage):
    """Newton Solver (MODFLOW-NWT only)"""


class LAK(_MFPackage):
    """Lake Package"""


class GAGE(_MFPackage):
    """Gage Package"""


class ETS(_MFPackage):
    """Evapotranspiration Segments Package"""


class DRT(_MFPackage):
    """Drain Return Package"""


class FHB(_MFPackage):
    """Flow and Head Boundary Package"""


class HYD(_MFPackage):
    """HYDMOD Package"""


class RES(_MFPackage):
    """Reservoir Package"""


class MNW(_MFPackage):
    """Multi-Node, Drawdown-Limited Well Package"""


class MNW1(MNW):
    """Multi-Node Well Package version 1"""


class MNW2(_MFPackage):
    """Multi-Node Well Package version 2"""


class MNWI(_MFPackage):
    """Multi-Node Well Information Package"""


class DAF(_MFPackage):
    """DAFLOW Package surface-water input file"""


class DAFG(_MFPackage):
    """DAFLOW Package ground-water input file"""


class STR(_MFPackage):
    """Stream Package"""


class SFR(_MFPackage):
    """Streamflow-Routing Package"""


class SWR(_MFPackage):
    """Surface-Water Routing Package"""


class KDEP(_MFPackage):
    """Hydraulic-Conductivity Depth-Dependence Capability of the HUF2 Package
    """


class LVDA(_MFPackage):
    """Model-Layer Variable-Direction Horizontal Anisotropy capability of the
    HUF2 Package"""


class SUB(_MFPackage):
    """Subsidence and Aquifer-System Compaction Package"""


class SWI2(_MFPackage):
    """Saltwater Intrusion Package"""


class LMT6(_MFPackage):
    """Link-MT3DMS Package"""


class OBS(_MFPackage):
    """Observation Process input file (MODFLOW-2000 only)"""


class ADV2(_MFPackage):
    """Advective-Transport Observation Input File (MODFLOW-2000 only)"""


class CHOB(_MFPackage):
    """Constant-Head Flow Observation Input File"""


class DROB(_MFPackage):
    """Drain Observation Input File"""


class DTOB(_MFPackage):
    """Drain Return Observation Input File (MODFLOW-2000 only)"""


class GBOB(_MFPackage):
    """General-Head-Boundary Observation Input File"""


class HOB(_MFPackage):
    """Head-Observation Input File"""


class RVOB(_MFPackage):
    """River Observation Input File"""


class STOB(_MFPackage):
    """Streamflow-Routing Observation Input File (MODFLOW-2000 only)"""


class CFP(_MFPackage):
    """Conduit Flow Process (MODFLOW-CFP only)"""


class CRCH(_MFPackage):
    """Conduit Recharge Package (MODFLOW-CFP only)"""


class COC(_MFPackage):
    """Conduit Output Control File (MODFLOW-CFP only)"""


class SEN(_MFPackage):
    """Sensitivity Process input file (MODFLOW-2000 only)"""


class PES(_MFPackage):
    """Parameter Estimation Process input file (MODFLOW-2000 only)"""


class ASP(_MFPackage):
    """PEST-ASP"""


class _MFData(object):
    pass


class GLOBAL(_MFData):
    """Global listing file. MODFLOW-2000 only."""


class LIST(_MFData):
    """Forward run listing file."""


def _get_packages():
    """Returns a dict of MODFLOW packages supported by moflow.mf"""
    global_dict = globals()
    packages = {}
    for key in global_dict:
        if key.startswith('_'):
            continue
        obj = global_dict[key]
        if inspect.isclass(obj) and issubclass(obj, (_MFPackage, _MFData)):
            packages[key] = obj
    return packages


class Modflow(object):
    """Base class for MODFLOW packages, based on Name File (nam)

    Each package can attach to this object as a lower-case attribute name
    of the package name.

    Example:
    >>> m = Modflow()
    >>> m.dis = DIS()
    >>> m.bas6 = BAS6()
    """

    @property
    def ref_dir(self):
        """Returns reference directory for MODFLOW files"""
        return getattr(self, '_ref_dir', '')

    @ref_dir.setter
    def ref_dir(self, value):
        path = str(value)
        if path and not os.path.isdir(path):
            self._logger.error("'ref_dir' is not a directory: '%s'", path)
        setattr(self, '_ref_dir', path)

    @property
    def prefix(self):
        """Returns prefix name of MODFLOW simulation files"""
        return getattr(self, '_prefix', None)

    @prefix.setter
    def prefix(self, value):
        if value is not None:
            if 'upper' not in value:
                raise ValueError("'prefix' is not string-like")
            elif ' ' in value:
                raise ValueError("spaces found in 'prefix' value")
        setattr(self, '_prefix', value)

    _logger = None
    _packages = None  # _MFPackage objects
    _nunit = None  # keys are integer nunit of either fpath str or file object
    data = None  # _MFData objects

    def __init__(self, *args, **kwargs):
        """Create a MODFLOW simulation"""
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

    def __repr__(self):
        """Representation of Modflow object, showing packages"""
        return '<%s: %s>' % (self.__class__.__name__, ', '.join(list(self)))

    def __getitem__(self, key):
        """Return package or data using nunit integer"""
        return self._nunit[key]

    def __setitem__(self, key, value):
        """Set package or data with nunit integer"""
        self._nunit[key] = value

    def __len__(self):
        """Returns number of packages, but not data or nunit items"""
        return len(self._packages)

    def __iter__(self):
        """Allow iteration through sequence of packages, but not data"""
        return iter(self._packages)

    def __setattr__(self, name, value):
        """Sets Modflow package object"""
        existing = getattr(self, name, None)
        if ((hasattr(self, name) or name.startswith('_')) and
                not isinstance(existing, _MFPackage)):
            # Set existing, non-Modflow package object as normal
            object.__setattr__(self, name, value)
        elif isinstance(value, _MFPackage):
            if name != value.__class__.__name__.lower():
                raise AttributeError("%r must have an attribute name %r" %
                                     (value.__class__.__name__,
                                      value.__class__.__name__.lower()))
            elif existing and existing.__class__ != value.__class__:
                self._logger.warn('attribute %r: replacing value of %r '
                                  ' with %r', name, existing.__class__,
                                  value.__class__)
            if name not in self._packages:
                self._packages.append(name)
                self._logger.debug('attribute %r: adding %r package',
                                   name, value.__class__.__name__)
                if isinstance(existing, _MFPackage):
                    self._logger.error('attribute %r: existed before, but was '
                                       'not found in _packages list', name)
            else:
                if existing is None:
                    self._logger.error('attribute %r: existed in _packages '
                                       'before it was an attribute', name)
                else:
                    self._logger.debug('attribute %r: replacing %r with '
                                       'different object', name,
                                       value.__class__.__name__)
            object.__setattr__(self, name, value)
        else:
            raise ValueError(("attribute %r (%r) must be a _MFPackage object "
                              "or other existing attribute.") % (name, value))

    def __delattr__(self, name):
        """Deletes package object"""
        self._logger.debug('delattr %r', name)
        if name in self._packages:
            del self._packages[self._packages.index(name)]
        object.__delattr__(self, name)

    def append(self, package):
        """Append a package to the end, using a default attribute"""
        if not isinstance(package, _MFPackage):
            raise ValueError("value must be a _MFPackage-related object; "
                             "found " + repr(package.__class__))
        name = package._attr_name
        if hasattr(self, name):
            raise ValueError(
                "attribute %r already exists; use setattr to replace" % name)
        setattr(self, name, package)
        if package.nam is None:
            package.nam = self
        elif package.nam is self:
            self._logger.debug('%s.nam already set', name)
        else:
            self._logger.error(
                "not setting %s.nam, since it is already assigned to %r",
                name, package.nam)
        if package.nunit:
            self[package.nunit] = package

    def read(self, fname, *args, **kwargs):
        """Read a MODFLOW simulation from a Name File (with *.nam extension)

        Use 'ref_dir' keyword to specify the reference directory relative to
        other files referenced in the Name File, otherwise it is assumed
        to be relative to the same as the Name File.
        """
        self._packages = []
        self._nunit = {}
        self.data = {}
        self._logger.info('reading Name File: %s', fname)
        with open(fname, 'r') as fp:
            lines = fp.readlines()
        if 'ref_dir' in kwargs:
            self.ref_dir = kwargs.pop('ref_dir')
            if self.ref_dir is None or not os.path.isdir(str(self.ref_dir)):
                self._logger.error("'ref_dir' is not a directory: %s",
                                   self.ref_dir)
                self.ref_dir = os.path.dirname(fname)
        else:
            self.ref_dir = os.path.dirname(fname)
        if args:
            self._logger.warn('unused arguments: %r', args)
        if kwargs:
            self._logger.warn('unused keyword arguments: %r', kwargs)
        # Use a separate logger to read the Name File
        log = logging.getLogger('NameFile')
        log.handlers = logger.handlers
        log.setLevel(logger.level)
        self._packages = []
        available_packages = _get_packages()
        dir_cache = {}
        for ln, line in enumerate(lines, start=1):
            line = line.rstrip()
            if len(line) == 0:
                log.debug('%d: skipping empty line', ln)
                continue
            elif len(line) > 199:
                log.warn('%d: has %d characters, but should be <= 199',
                         ln, len(line))
            if line.startswith('#'):
                log.debug('%d: skipping comment: %s', ln, line[1:])
                continue
            # 1: Ftype Nunit Fname [Option]
            dat = line.split()
            if len(dat) < 3:
                raise ValueError(
                    'line %d has %d items, but 3 or 4 are expected' %
                    (ln, len(dat)))
            ftype, nunit, fname = dat[:3]
            if len(dat) >= 4:
                option = dat[3].upper()
            else:
                option = None
            if len(dat) > 4:
                log.info('%d: ignoring remaining items: %r', ln, dat[4:])
            # Ftype is the file type, which may be entered in all uppercase,
            # all lowercase, or any combination.
            ftype = ftype.upper()
            if ftype.startswith('DATA'):
                obj = _MFData()
            elif ftype in available_packages:
                obj = available_packages[ftype]()
                assert obj.__class__.__name__ == ftype,\
                    (obj.__class__.__name__, ftype)
            else:
                log.warn("%d:ftype: %r not identified as a supported "
                         "file type", ln, ftype)
                obj = _MFPackage()
            # set back-references for NameFile and Nunit
            obj.nam = self
            obj.nunit = nunit = int(nunit)
            try:
                self[nunit] = obj
            except KeyError:
                log.warn("%d:nunit: %s already assigned for %r",
                         ln, nunit, self[nunit].__class__.__name__)
            orig_fname = fname
            fname = fname.strip('"')
            if os.path.sep == '/':  # for reading on POSIX systems
                if '\\' in fname:
                    fname = fname.replace('\\', '/')
            fpath = os.path.join(self.ref_dir, fname)
            if not os.path.isfile(fpath):
                test_dir, test_fname = os.path.split(fname)
                pth = os.path.join(self.ref_dir, test_dir)
                if os.path.isdir(pth):
                    if pth not in dir_cache:
                        dir_cache[pth] = \
                            dict([(f.lower(), f) for f in os.listdir(pth)])
                    fname_key = test_fname.lower()
                    if fname_key in dir_cache[pth]:
                        fname = os.path.join(
                            test_dir, dir_cache[pth][fname_key])
                        fpath = os.path.join(pth, dir_cache[pth][fname_key])
                        assert os.path.isfile(fpath), fpath
            if orig_fname != fname:
                log.info("%d:fname: changed from '%s' to '%s'",
                         ln, orig_fname, fname)
            obj.fname = fname
            obj.fpath = fpath
            fpath_exists = os.path.isfile(obj.fpath)
            if isinstance(obj, _MFPackage) and not fpath_exists:
                log.warn("%d:fname: '%s' does not exist in '%s'",
                         ln, obj.fname, self.ref_dir)
            # Interpret option
            if option == 'OLD':
                # the file must exist when MODFLOW has started
                if ftype.startswith('DATA') and not fpath_exists:
                    log.warn("%d:option:%r, but file does not exist",
                             ln, option)
            elif option == 'REPLACE':
                if ftype.startswith('DATA') and fpath_exists:
                    log.debug("%d:option:%r: file exists and will be replaced",
                              ln, option)
            obj.nam_option = option
            if isinstance(obj, _MFPackage):
                setattr(self, obj._attr_name, obj)
        log.debug('finished reading %d lines', ln)
        del log
        self._logger.info('reading data from %d packages', len(self))
        # Read prerequisite packages first
        if hasattr(self, 'dis'):
            dis_mode = 'dis'
        elif hasattr(self, 'disu'):
            dis_mode = 'disu'
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
