# -*- coding: utf-8 -*-
import re
from enum import Enum
from warnings import warn

from . import MFIO

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict


_re_conv = re.compile(r'^([sifb])(\d*)$')
_re_conv_fmt = {}


def _proc_fmt(fmt):
    """Process fmt code and optional width

    Parameters:
    -----------
        fmt : str
            Format code; see `conv`

    Returns:
    --------
    (code, width)
    """
    if fmt in _re_conv_fmt:
        code, width = _re_conv_fmt[fmt]
    else:
        m = _re_conv.findall(fmt)
        if not m:
            raise ValueError(
                "fmt {0!r} does not match pattern '{1}'"
                .format(fmt, _re_conv.pattern))
        code, width = m[0]
        if width:
            width = int(width)
            if width <= 0:
                raise ValueError("'width' must be greater than zero")
        else:
            width = None
        _re_conv_fmt[fmt] = code, width
    return code, width


def conv(item, fmt, on_blank=None):
    """Convert item to from fmt to a Python value

    Parameters
    ----------
    item : str
        Item to convert
    fmt : str
        Format code with one letter and optional width, e.g. 'i10'. Letter
        can be 's' for string, 'i' for int, 'f' for float, or 'b' for bool.
    on_blank : None, or a default value
        If item is blank, return None, or a default value (cast with the fmt,
        code)

    Returns
    -------
    Value converted to Python type.

    Raises
    ------
    ValueError
        If the Item cannot be converted, or cannot understand fmt.
    """
    code, width = _proc_fmt(fmt)
    if width and len(item) > width:
        warn('{0!r} longer than width {1}'.format(item, width))
        item = item[:width]
    item = item.strip()
    if item == '':
        if on_blank is None:
            return None
        item = on_blank
    try:
        if code == 's':
            conv_item = item
        elif code == 'i':
            conv_item = int(item)
        elif code == 'f':
            conv_item = float(item)
        elif code == 'b':
            if item.upper() in ('T', 'TRUE', '.TRUE.', '1'):
                conv_item = True
            elif item.upper() in ('F', 'FALSE', '.FALSE.', '0'):
                conv_item = False
            else:
                raise ValueError()
        else:
            raise ValueError('unknown use for {0!r}'.format(code))
    except ValueError:
        raise ValueError(
            'cannot convert {0!r} to fmt code {1!r}'.format(item, fmt))
    return conv_item


class TextFile(MFIO):
    """Any formatted text file with data sets"""
    fixed = None  # fixed or free format
    lines = None  # list of raw line data
    lineno = None  # line number
    dsid = None  # data set identifier
    delimiter = None  # default delimiter, if not whitespace / free

    def __init__(self, parent, **kwargs):
        MFIO.__init__(self, parent=parent)
        self.lineno = None
        self.dsid = None
        self.lines = []
        if 'fixed' in kwargs:
            self.fixed = self.parent._fixed = kwargs.pop('fixed')
            self.log.debug('setting fixed=%r', self.fixed)
        else:
            self.fixed = getattr(self.parent, '_fixed', None)
        # Get a refrence to any unit numbers to open external files
        if hasattr(parent, 'nam') and hasattr(parent.nam, 'nunit'):
            self.nunit = parent.nam.nunit
        else:
            self.nunit = {}
        return

    def __len__(self):
        """Returns number of lines"""
        return len(self.lines)


class OnError(Enum):
    '''Actions to take when encountering an error'''
    zero = 0
    default = 1
    value_error = 2
    none = 3


class TextFileReader(TextFile):
    """Reader for formatted text file with data sets"""

    def __init__(self, parent, fname, **kwargs):
        TextFile.__init__(self, parent=parent)
        if hasattr(fname, 'upper'):
            self.log.info('reading file %s', fname)
            # Read whole file at once, then close it
            with open(fname, 'r') as fp:
                self.lines = fp.readlines()
        elif hasattr(fname, 'readlines'):
            self.log.info('reading lines from %r', fname)
            self.lines = fname.readlines()
        else:
            raise TypeError(
                "'fname' does not appear to be a file name or object: " +
                repr(fname))
        self.lineno = getattr(fname, 'lineno', 0)
        self.closed = False
        self.dsid = None
        return

    @property
    def not_eof(self):
        """Reader is not at the end of file (EOF)"""
        return self.lineno < len(self.lines)

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

    def curinfo(self, delta=0):
        """Returns line and data set identifier info"""
        lineno = self.lineno
        if delta:
            try:
                lineno += delta
            except:
                pass
        return str(lineno) + ':data set ' + str(self.dsid)

    @property
    def curline(self):
        """Return the current line"""
        try:
            if self.lineno == 0:
                return ''
            else:
                return self.lines[self.lineno - 1]
        except IndexError:
            raise IOError('Unexpected end of file')

    def nextline(self, dsid=None):
        """Return the next line and increment lineno"""
        if dsid is not None:
            self.dsid = dsid
            self.log.debug('%s:using nextline', self.curinfo(True))
        self.lineno += 1
        try:
            line = self.lines[self.lineno - 1]
        except IndexError:
            self.lineno -= 1
            raise IOError('Unexpected end of file')
        if dsid is not None:
            self.log.debug('%s:returning line with length %d:%r',
                           self.curinfo(), len(line), line)
        return line

    def readline(self):
        """Alias to nextline"""
        return self.nextline()

    def getitem(self, dsid=None, startnextline=True, fmt=None,
                on_error=OnError.default):
        """Get one item"""
        if dsid is not None:
            self.dsid = dsid
            msg = 'using getitem'
            if not startnextline:
                msg += ' on current line'
            msg += ' with fmt=' + repr(fmt)
            self.log.debug(
                '%s:%s', self.curinfo(startnextline), msg)
        code, width = _proc_fmt(fmt)
        if on_error == OnError.default:
            if width:
                on_error = OnError.zero
            else:
                on_error = OnError.value_error
        if startnextline:
            line = self.nextline()
        else:
            line = self.curline
        if width:
            line = line[:width].strip()
        else:
            line = line.strip()
        if line == '':
            if on_error == OnError.zero:
                line = '0'
            if on_error == OnError.none:
                return None
            elif on_error == OnError.value_error:
                msg = '%s:%s' % (self.curinfo(), "empty input for 'getitem'")
                self.log.error(msg)
                raise ValueError(msg)
            else:
                raise KeyError(
                    "unhandled 'on_error' condition: " + repr(on_error))
        if not width:
            dat = line.split()[0]
            
        

    def getitems(self, dsid=None, startnextline=True, multiline=False,
                 fmts=None, on_error=ValueError):
        """Get items from one or more lines (if multiline) into a list

        If num_items is defined, then only this count will be returned and any
        remainding items from the line will be ignored. If num_items is a
        tuple, it will be (num_required, num_optional). If multiline and not
        enough items are found, None is set. To read fixed width formats,
        pass a list of character widths that is the same length as num_items,
        or of the sum of the tuple.
        """
        if not isinstance(fmts, (list, tuple)):
            raise ValueError("'fmts' must be a list or tuple of formats")
        elif len(fmts) < 1:
            raise ValueError("at least one 'fmts' must be supplied")
        num_items = len(fmts)
        codes = []
        widths = []
        for fmt in fmts:
            code, width = _proc_fmt(fmt)
            codes.append(code)
            widths.append(width)
        if dsid is not None:
            self.dsid = dsid
            if num_items == 1:
                msg = 'one item'
            else:
                msg = str(num_items) + ' items'
            if multiline:
                msg += ' over multiple lines'
            if widths:
                msg += ' with fixed widths ' + str(widths)
            if not startnextline:
                msg += ', starting on the current line'
            self.log.debug(
                '%s:using getitems for %s', self.curinfo(startnextline), msg)
        # Gather items
        items = []
        if multiline:
            if widths:
                self.log.error("widths ignored for multiline")
            while len(items) < num_items:
                try:
                    line = self.nextline()
                except IOError:
                    message = ('Unexpected end of file, read %d '
                               'of requested %d items') % \
                              (len(items), num_items)
                    raise IOError(message)
                if self.delimiter:
                    line = line.replace(self.delimiter, ' ')
                items += line.split()
        else:
            if startnextline:
                line = self.nextline()
            else:
                line = self.curline
            if widths:  # fixed width
                pos = 0
                for w in widths:
                    item = line[pos:pos + w]
                    if len(item) == 0:
                        break
                    items.append(item)
                    pos += w
            else:  # free
                if self.delimiter:
                    line = line.replace(self.delimiter, ' ')
                items = line.split()
        if len(items) > num_items:
            # trim off too many
            items = items[:num_items]
        elif len(items) < num_items:
            self.log.debug(
                ('%s:requested %d item%s, but found %d; '
                 "remaining %d will be None"),
                self.curinfo(),
                num_items, '' if num_items == 1 else 's',
                len(items), (num_items - len(items)))
            items += [None] * (num_items - len(items))
        # Convert format
        assert len(codes) == len(items)
        for idx in range(len(items)):
            if codes[idx]:
                items[idx] = self.conv(items[idx], codes[idx], idx1=idx + 1)
        if dsid is not None:
            self.log.debug(
                '%s:returning %d items:%r', self.curinfo(), len(items), items)
        return items

    def getnameditems(self, dsid, required=None, optional=[]):
        """Get items into an OrderedDict"""
        if dsid is not None:
            if required is None:
                if (getattr(self.parent, '_format', None) and
                        dsid in self.parent._format):
                    required = self.parent._format[dsid]
                else:
                    raise ValueError(
                        "'required' missing for " + str(dsid))
            if (not optional and getattr(self.parent, '_optional', None) and
                    dsid in self.parent._optional):
                optional = self.parent._optional[dsid]
            self.dsid = dsid
            if optional:
                and_opt = ' and %d optional' % (len(optional),)
            else:
                and_opt = ''
            self.log.debug(
                '%s:using getnameditems for %d required%s items',
                self.curinfo(True), len(required), and_opt)
        if required is None:
            raise ValueError('required must be specified')
        num_items = (len(required), len(optional))
        if self.fixed:
            widths = []
            for n, f in required + optional:
                try:
                    m = _re_conv.match(f)
                    widths.append(int(m.groups()[1]))
                except:
                    self.log.warn("%s:cannot match %r from '%s'",
                                  n, f, _re_conv.pattern)
                    widths = None
                    break
        else:  # free
            widths = None
        items = self.getitems(None, num_items, widths=widths)
        res = OrderedDict()
        for idx1, (name, fmt) in enumerate(required, 1):
            self.conv(items, fmt, name, idx1, res)
        for idx1, (name, fmt) in enumerate(optional, 1 + idx1):
            self.conv(items, fmt, name, idx1, res, optional=True)
        if items:
            self.log.warn('remaining items: %r', items)
        if data_set_num is not None:
            self.log.debug(
                '%s:returning %d items:%s',
                self.curinfo(), len(res),
                ', '.join(['%s=%r' % i for i in res.items()]))
        return res
