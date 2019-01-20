# -*- coding: utf-8 -*-

import pytest
import sys

from numpy import testing
from textwrap import dedent

from moflow import logger, logging
from moflow.io.textfile import conv, TextFileReader

if sys.version_info[0] < 3:
    from io import BytesIO
    StringIO = BytesIO
else:
    from io import StringIO, BytesIO

logger.level = logging.DEBUG


def test_conv():
    assert conv('1', 's') == '1'
    assert conv(' word ', 's') == 'word'
    assert conv('word', 's2') == 'wo'
    assert conv('', 's') is None
    assert conv('', 'i') is None
    assert conv('1', 'i') == 1
    assert conv('1', 'i10') == 1
    assert conv('         1', 'i10') == 1
    assert conv('    1     ', 'i10') == 1
    assert conv('1.2', 'f') == 1.2
    assert conv('-1e-30', 'f') == -1e-30
    assert conv('true', 'b') is True
    assert conv('false', 'b') is False
    assert conv('1', 'b') is True
    assert conv('0', 'b') is False


class Parent(object):
    pass


def xtest_io_reader_basics():
    p = Parent()
    f = StringIO(dedent('''\
        Any content on  a line.
        100 ignore
        200 -2.4E-12
        4 500 FREE
        -44 888.0
        last line
    '''))
    r = TextFileReader(p, f)
    assert r.not_eof
    assert r.lineno == 0
    assert len(r) == 6
    assert r.curline == ''
    # 0: Text
    line = r.nextline(0)
    assert r.lineno == 1
    assert line == 'Any content on  a line.\n'
    # 1: an item
    assert r.getitems(1, fmt='i') == [100]
    assert r.lineno == 2
    # 2: two named items
    with pytest.raises(ValueError):
        r.read_named_items(2, ('par1', 'par2'), 'i')
    r.lineno -= 1  # manually scroll back 1 line and try again
    r.read_named_items(2, ('par1', 'par2'), 'f')
    assert p.par1 == 200.0
    testing.assert_almost_equal(p.par2, -2.4E-12)
    # 3: three named items
    items = r.get_named_items(3, ['a', 'b'], 'f')
    assert items == {'a': 4.0, 'b': 500.0}
    # 4: two named items
    r.read_named_items(4, ['par1', 'par2'], 'f')
    assert p.par1 == -44.0
    testing.assert_almost_equal(p.par2, 888.0)
    # post-Data Set
    assert r.not_eof
    assert r.nextline() == 'last line\n'
    assert r.lineno == 6
    assert not r.not_eof
    # Try to read past EOF
    with pytest.raises(IndexError):
        r.nextline()
    assert r.lineno == 6
