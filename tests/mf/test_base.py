import numpy as np
import os
import pytest
import sys

from numpy import testing
from textwrap import dedent

from moflow.mf.name import Modflow
from moflow.mf.base import MFPackage
from moflow.mf.reader import MFFileReader

if sys.version_info[0] < 3:
    from io import BytesIO
    StringIO = BytesIO
else:
    from io import StringIO, BytesIO


class ExamplePackage(MFPackage):
    par1 = None
    par2 = None


def test_mf_reader_basics():
    p = ExamplePackage()
    f = StringIO(dedent('''\
        # A comment
        100 ignore
        200 -2.4E-12
        4 500 FREE
        -44 888.0
        last line
    '''))
    r = MFFileReader(f, p)
    assert r.not_eof
    assert r.lineno == 0
    assert len(r) == 6
    # 0: Text
    r.read_text()
    assert r.lineno == 1
    assert p.text == ['A comment']
    # 1: an item
    assert r.get_items(1, 1, 'i') == [100]
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


def test_mf_reader_empty():
    p = ExamplePackage()
    f = StringIO('# Empty file')
    r = MFFileReader(f, p)
    assert r.not_eof
    assert r.lineno == 0
    assert len(r) == 1
    # Item 0: Text
    r.read_text()
    assert r.lineno == 1
    assert p.text == ['Empty file']
    assert not r.not_eof


def test_mf_read_free_arrays():
    # Examples from page 8-59 of TM6A16_MF2005
    m = Modflow()
    p = ExamplePackage()
    m.append(p)
    f = StringIO(dedent('''\
    CONSTANT  5.7     This sets an entire array to the value "5.7".
    INTERNAL  1.0  (7F4.0)  3    This reads the array values from the ...
     1.2 3.7 9.3 4.2 2.2 9.9 1.0
     3.3 4.9 7.3 7.5 8.2 8.7 6.6
     4.5 5.7 2.2 1.1 1.7 6.7 6.9
     7.4 3.5 7.8 8.5 7.4 6.8 8.8
    EXTERNAL 52  1.0 (7F4.0)  3   This reads the array from the formatted..
    EXTERNAL 47 1.0 (BINARY)  3   This reads the array from the binary ...
    OPEN/CLOSE  test.dat  1.0  (7F4.0)  3 This reads the array from the ...
    '''))
    # Prepare ASCII data for unit 52, and for test.dat
    d2_str = (
        ' 1.2 3.7 9.3 4.2 2.2 9.9 1.0\n'
        ' 3.3 4.9 7.3 7.5 8.2 8.7 6.6\n'
        ' 4.5 5.7 2.2 1.1 1.7 6.7 6.9\n'
        ' 7.4 3.5 7.8 8.5 7.4 6.8 8.8\n'
    )
    m[52] = StringIO(d2_str)
    # Prepare binary data for unit 47
    d2_expected = np.array(
        [[1.2, 3.7, 9.3, 4.2, 2.2, 9.9, 1.0],
         [3.3, 4.9, 7.3, 7.5, 8.2, 8.7, 6.6],
         [4.5, 5.7, 2.2, 1.1, 1.7, 6.7, 6.9],
         [7.4, 3.5, 7.8, 8.5, 7.4, 6.8, 8.8]], 'f')
    m[47] = BytesIO(d2_expected.tostring())
    r = MFFileReader(f, p)
    # Data Number 1: Read constant 4x5 array
    d1_shape = (4, 7)
    d1_expected = np.ones(d1_shape, 'f') * 5.7
    d1 = r.get_array(1, d1_shape, 'f', return_dict=True)
    assert not hasattr(d1, 'locat')
    assert d1['cntrl'] == 'CONSTANT'
    assert d1['cnstnt'] == '5.7'
    assert d1['text'] == 'This sets an entire array to the value "5.7".'
    testing.assert_array_equal(d1['array'], d1_expected)
    assert r.lineno == 1
    # Data Number 2: Read internal 4x7 array
    d2_shape = (4, 7)
    d2 = r.get_array(2, d2_shape, 'f', return_dict=True)
    assert d2['cntrl'] == 'INTERNAL'
    assert d2['cnstnt'] == '1.0'
    assert d2['fmtin'] == '(7F4.0)'
    assert d2['iprn'] == '3'
    assert d2['text'] == 'This reads the array values from the ...'
    testing.assert_array_equal(d2['array'], d2_expected)
    assert r.lineno == 6
    # Data Number 3: EXTERNAL ASCII
    d3 = r.get_array(3, d2_shape, 'f', return_dict=True)
    assert d3['cntrl'] == 'EXTERNAL'
    assert d3['nunit'] == 52
    assert d3['cnstnt'] == '1.0'
    assert d3['fmtin'] == '(7F4.0)'
    assert d3['iprn'] == '3'
    testing.assert_array_equal(d3['array'], d2_expected)
    assert r.lineno == 7
    # Data Number 4: EXTERNAL BINARY
    d4 = r.get_array(4, d2_shape, 'f', return_dict=True)
    assert d4['cntrl'] == 'EXTERNAL'
    assert d4['nunit'] == 47
    assert d4['cnstnt'] == '1.0'
    assert d4['fmtin'] == '(BINARY)'
    assert d4['iprn'] == '3'
    testing.assert_array_equal(d4['array'], d2_expected)
    assert r.lineno == 8
    # Data Number 5: OPEN/CLOSE test.dat
    d5_fname = 'test.dat'
    with open(d5_fname, 'w') as fp:
        fp.write(d2_str)
    d5 = r.get_array(5, d2_shape, 'f', return_dict=True)
    os.unlink(d5_fname)
    assert d5['cntrl'] == 'OPEN/CLOSE'
    assert d5['fname'] == d5_fname
    assert d5['cnstnt'] == '1.0'
    assert d5['fmtin'] == '(7F4.0)'
    assert d5['iprn'] == '3'
    testing.assert_array_equal(d5['array'], d2_expected)
    assert r.lineno == 9
    assert not r.not_eof


def test_mf_read_fixed_arrays():
    m = Modflow()
    p = ExamplePackage()
    p.nunit = 11
    m.append(p)
    f = StringIO('''\
        11        1. (15f4.0)                    7  WETDRY-1
  2.  2.  2.  2.  2.  2.  2.  2. -2. -2. -2. -2. -2. -2. -2.
  2.  2.  2.  2.  2.  2.  2.  2. -2. -2. -2. -2. -2. -2. -2.
  2.  2.  2. -2.  2.  2.  2.  2. -2. -2. -2. -2. -2. -2. -2.
  2.  2.  2.  2.  2.  2.  2.  2. -2. -2. -2. -2. -2. -2. -2.
  2.  2.  2.  2.  2.  2.  2.  2. -2. -2. -2. -2. -2. -2. -2.
  2.  2.  2. -2.  2.  2.  2.  2. -2. -2. -2. -2. -2. -2. -2.
  2.  2.  2.  2.  2.  2.  2.  2. -2. -2. -2. -2. -2. -2. -2.
        11         1(12I2)                       3
 1 1 1 1 1 1 1 1 1 1 1 1
 1 1 9 1 1 1 1 1 1 1 1 1
        11         1(13I3)                                  IBOUND        L1
 -1  1  1  1  1  1  1  1  1  1  1  1 -1
        11         1(13I3)                                  IBOUND        L2
 -1  1  1  1  1  1  1  1  1  1  1  1 -1
         0        6. (15f4.0)                    7  # Some text
         0         8(12I2)                       3
       -17        1. (binary)                    7
        16         1(24I3)                       3
        16         1(24I3)                       3
         0      145.
''')
    # Prepare two ASCII data sets for unit 16
    m[16] = StringIO('''\
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  1  1  1  1  1  0  0  0  0  0  0
  0  0  0  0  0  0  1  1  1  1  1  0  0  0  0  0  0
  0  0  0  0  0  0  1  1  1  1  1  0  0  0  0  0  0
  0  0  0  0  0  0  1  1  1  1  1  0  0  0  0  0  0
  0  0  0  0  0  0  1  1  1  1  1  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  1  1  1  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  1  1  1  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  1  1  1  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
''')
    # Prepare binary data for unit 17
    d6_expected = np.array(
        [[1.2, 3.7, 9.3, 4.2, 2.2, 9.9, 1.0],
         [3.3, 4.9, 7.3, 7.5, 8.2, 8.7, 6.6],
         [4.5, 5.7, 2.2, 1.1, 1.7, 6.7, 6.9],
         [7.4, 3.5, 7.8, 8.5, 7.4, 6.8, 8.8]], 'f')
    m[17] = BytesIO(d6_expected.tostring())
    r = MFFileReader(f, p)
    # Data Number 1
    d1_shape = (7, 15)
    a = [[2.] * 8 + [-2.] * 7]
    b = [[2.] * 3 + [-2.] + [2.] * 4 + [-2.] * 7]
    d1_expected = np.array(a * 2 + b + a * 2 + b + a)
    d1 = r.get_array(1, d1_shape, 'f', return_dict=True)
    assert not hasattr(d1, 'cntrl')
    assert d1['locat'] == 11
    assert d1['cnstnt'] == '1.'
    assert d1['fmtin'] == '(15F4.0)'
    assert d1['iprn'] == '7'
    assert d1['text'] == 'WETDRY-1'
    testing.assert_array_equal(d1['array'], d1_expected)
    assert r.lineno == 8
    # Data Number 2
    d2_shape = (2, 12)
    d2_expected = np.ones(d2_shape)
    d2_expected[1, 2] = 9
    d2 = r.get_array(2, d2_shape, 'i', return_dict=True)
    assert d2['locat'] == 11
    assert d2['cnstnt'] == '1'
    assert d2['fmtin'] == '(12I2)'
    assert d2['iprn'] == '3'
    assert not hasattr(d2, 'text')
    testing.assert_array_equal(d2['array'], d2_expected)
    assert r.lineno == 11
    # Data Number 3
    d3_shape = (2, 13)
    d3_expected = np.array(2 * [[-1] + [1] * 11 + [-1]], 'i')
    d3a = np.empty(d3_shape, 'i')
    for ilay in range(d3_shape[0]):
        d3 = r.get_array(3, d3_shape[1], 'i', return_dict=True)
        assert d3['locat'] == 11
        assert d3['fmtin'] == '(13I3)'
        assert d3['iprn'] == ''
        assert d3['text'].startswith('IBOUND')
        d3a[ilay, :] = d3['array']
    assert d3['text'] == 'IBOUND        L2'
    testing.assert_array_equal(d3a, d3_expected)
    assert r.lineno == 15
    # Data Number 4
    d4_shape = (4, 8)
    d4_expected = np.ones(d4_shape, 'f') * 6
    d4 = r.get_array(4, d4_shape, 'f', return_dict=True)
    assert d4['locat'] == 0
    assert d4['cnstnt'] == '6.'
    assert d4['fmtin'] == '(15F4.0)'
    assert d4['iprn'] == '7'
    assert d4['text'] == 'Some text'
    testing.assert_array_equal(d4['array'], d4_expected)
    assert r.lineno == 16
    # Data Number 5
    d5_shape = (7, 6)
    d5_expected = np.ones(d5_shape) * 8
    d5 = r.get_array(5, d5_shape, 'i', return_dict=True)
    assert d5['locat'] == 0
    assert d5['cnstnt'] == '8'
    assert d5['fmtin'] == '(12I2)'
    assert d5['iprn'] == '3'
    assert not hasattr(d5, 'text')
    testing.assert_array_equal(d5['array'], d5_expected)
    assert r.lineno == 17
    # Data Number 6
    d6_shape = (4, 7)
    d6 = r.get_array(6, d6_shape, 'f', return_dict=True)
    assert d6['locat'] == -17
    assert d6['cnstnt'] == '1.'
    assert d6['fmtin'] == '(BINARY)'
    assert d6['iprn'] == '7'
    assert not hasattr(d6, 'text')
    testing.assert_array_equal(d6['array'], d6_expected)
    assert r.lineno == 18
    # Data Number 7
    d7_shape = (2, 17, 17)
    d7_expected = np.zeros(d7_shape, 'i')
    d7_expected[0, 6:11, 6:11] = 1
    d7_expected[1, 7:10, 7:10] = 1
    d7a = np.empty(d7_shape, 'i')
    for ilay in range(d7_shape[0]):
        d7 = r.get_array(7, d7_shape[1:], 'i', return_dict=True)
        assert d7['locat'] == 16
        assert d7['fmtin'] == '(24I3)'
        assert d7['iprn'] == '3'
        assert not hasattr(d7, 'text')
        d7a[ilay, :] = d7['array']
    testing.assert_array_equal(d7a, d7_expected)
    assert r.lineno == 20
    # Data Number 8
    d8_shape = (2, 3)
    d8_expected = 145.0 * np.ones(d8_shape, 'f')
    d8 = r.get_array(8, d8_shape, 'f', return_dict=True)
    assert d8['locat'] == 0
    assert d8['cnstnt'] == '145.'
    assert not hasattr(d8, 'fmtin')
    assert not hasattr(d8, 'iprn')
    testing.assert_array_equal(d8['array'], d8_expected)
    assert r.lineno == 21
    assert not r.not_eof
