import os
import sys
import unittest
import numpy as np
from glob import glob
from io import BytesIO
from textwrap import dedent

try:
    from moflow import mf
except ImportError:
    os.chdir('..')
    sys.path.append('.')
    from moflow import mf

import logging
#mf.logger.level = logging.DEBUG
#mf.logger.level = logging.INFO
mf.logger.level = logging.WARN
#mf.logger.level = logging.ERROR


class TestPackage(mf._MFPackage):
    par1 = None
    par2 = None


class TestMFPackage(unittest.TestCase):

    def test_mf_reader_basic(self):
        p = TestPackage()
        f = BytesIO(dedent('''\
            # A comment
            100 ignore
            200 -2.4E-12
            4 500 FREE
            -44 888.0
            last line
        '''))
        r = mf._MFFileReader(f, p)
        self.assertTrue(r.not_eof)
        self.assertEqual(r.lineno, 0)
        self.assertEqual(len(r), 6)
        # 0: Text
        r.read_text()
        self.assertEqual(r.lineno, 1)
        self.assertEqual(p.text, ['A comment'])
        # 1: an item
        self.assertEqual(r.get_items(1, 1, 'i'), [100])
        self.assertEqual(r.lineno, 2)
        # 2: two named items
        self.assertRaises(ValueError, r.read_named_items,
                          2, ('par1', 'par2'), 'i')
        r.lineno -= 1  # manually scroll back 1 line and try again
        r.read_named_items(2, ('par1', 'par2'), 'f')
        self.assertEqual(p.par1, 200.0)
        self.assertAlmostEqual(p.par2, -2.4E-12)
        # 3: three named items
        items = r.get_named_items(3, ['a', 'b'], 'f')
        self.assertEqual(items, {'a': 4.0, 'b': 500.0})
        # 4: two named items
        r.read_named_items(4, ['par1', 'par2'], 'f')
        self.assertEqual(p.par1, -44.0)
        self.assertAlmostEqual(p.par2, 888.0)
        # post-Data Set
        self.assertTrue(r.not_eof)
        self.assertEqual(r.next_line(), 'last line\n')
        self.assertEqual(r.lineno, 6)
        self.assertFalse(r.not_eof)
        # Try to read past EOF
        self.assertRaises(IndexError, r.next_line)
        self.assertEqual(r.lineno, 6)

    def test_mf_reader_empty(self):
        p = TestPackage()
        f = BytesIO(dedent('''# Empty file'''))
        r = mf._MFFileReader(f, p)
        self.assertTrue(r.not_eof)
        self.assertEqual(r.lineno, 0)
        self.assertEqual(len(r), 1)
        # Item 0: Text
        r.read_text()
        self.assertEqual(r.lineno, 1)
        self.assertEqual(p.text, ['Empty file'])
        self.assertFalse(r.not_eof)

    def test_mf_read_free_arrays(self):
        # Examples from page 8-59 of TM6A16_MF2005
        m = mf.Modflow()
        p = TestPackage()
        m.append(p)
        f = BytesIO(dedent('''\
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
        m[52] = BytesIO(d2_str)
        # Prepare binary data for unit 47
        d2_expected = np.array(
            [[1.2, 3.7, 9.3, 4.2, 2.2, 9.9, 1.0],
             [3.3, 4.9, 7.3, 7.5, 8.2, 8.7, 6.6],
             [4.5, 5.7, 2.2, 1.1, 1.7, 6.7, 6.9],
             [7.4, 3.5, 7.8, 8.5, 7.4, 6.8, 8.8]], 'f')
        m[47] = BytesIO(d2_expected.tostring())
        r = mf._MFFileReader(f, p)
        # Data Number 1: Read constant 4x5 array
        d1_shape = (4, 7)
        d1_expected = np.ones(d1_shape, 'f') * 5.7
        d1 = r.get_array(1, d1_shape, 'f', return_dict=True)
        self.assertFalse(hasattr(d1, 'locat'))
        self.assertEqual(d1['cntrl'], 'CONSTANT')
        self.assertEqual(d1['cnstnt'], '5.7')
        self.assertEqual(d1['text'],
                         'This sets an entire array to the value "5.7".')
        self.assertEqual(d1['array'].shape, d1_expected.shape)
        self.assertTrue((d1['array'] == d1_expected).all())
        self.assertEqual(r.lineno, 1)
        # Data Number 2: Read internal 4x7 array
        d2_shape = (4, 7)
        d2 = r.get_array(2, d2_shape, 'f', return_dict=True)
        self.assertEqual(d2['cntrl'], 'INTERNAL')
        self.assertEqual(d2['cnstnt'], '1.0')
        self.assertEqual(d2['fmtin'], '(7F4.0)')
        self.assertEqual(d2['iprn'], '3')
        self.assertEqual(d2['text'],
                         'This reads the array values from the ...')
        self.assertEqual(d2['array'].shape, d2_expected.shape)
        self.assertTrue((d2['array'] == d2_expected).all())
        self.assertEqual(r.lineno, 6)
        # Data Number 3: EXTERNAL ASCII
        d3 = r.get_array(3, d2_shape, 'f', return_dict=True)
        self.assertEqual(d3['cntrl'], 'EXTERNAL')
        self.assertEqual(d3['nunit'], 52)
        self.assertEqual(d3['cnstnt'], '1.0')
        self.assertEqual(d3['fmtin'], '(7F4.0)')
        self.assertEqual(d3['iprn'], '3')
        self.assertEqual(d3['array'].shape, d2_expected.shape)
        self.assertTrue((d3['array'] == d2_expected).all())
        self.assertEqual(r.lineno, 7)
        # Data Number 4: EXTERNAL BINARY
        d4 = r.get_array(4, d2_shape, 'f', return_dict=True)
        self.assertEqual(d4['cntrl'], 'EXTERNAL')
        self.assertEqual(d4['nunit'], 47)
        self.assertEqual(d4['cnstnt'], '1.0')
        self.assertEqual(d4['fmtin'], '(BINARY)')
        self.assertEqual(d4['iprn'], '3')
        self.assertEqual(d4['array'].shape, d2_expected.shape)
        self.assertTrue((d4['array'] == d2_expected).all())
        self.assertEqual(r.lineno, 8)
        # Data Number 5: OPEN/CLOSE test.dat
        d5_fname = 'test.dat'
        with open(d5_fname, 'w') as fp:
            fp.write(d2_str)
        d5 = r.get_array(5, d2_shape, 'f', return_dict=True)
        os.unlink(d5_fname)
        self.assertEqual(d5['cntrl'], 'OPEN/CLOSE')
        self.assertEqual(d5['fname'], d5_fname)
        self.assertEqual(d5['cnstnt'], '1.0')
        self.assertEqual(d5['fmtin'], '(7F4.0)')
        self.assertEqual(d5['iprn'], '3')
        self.assertEqual(d5['array'].shape, d2_expected.shape)
        self.assertTrue((d5['array'] == d2_expected).all())
        self.assertEqual(r.lineno, 9)
        self.assertFalse(r.not_eof)

    def test_mf_read_fixed_arrays(self):
        m = mf.Modflow()
        p = TestPackage()
        p.nunit = 11
        m.append(p)
        f = BytesIO('''\
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
        m[16] = BytesIO('''\
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
        r = mf._MFFileReader(f, p)
        # Data Number 1
        d1_shape = (7, 15)
        a = [[2.] * 8 + [-2.] * 7]
        b = [[2.] * 3 + [-2.] + [2.] * 4 + [-2.] * 7]
        d1_expected = np.array(a * 2 + b + a * 2 + b + a)
        d1 = r.get_array(1, d1_shape, 'f', return_dict=True)
        self.assertFalse(hasattr(d1, 'cntrl'))
        self.assertEqual(d1['locat'], 11)
        self.assertEqual(d1['cnstnt'], '1.')
        self.assertEqual(d1['fmtin'], '(15F4.0)')
        self.assertEqual(d1['iprn'], '7')
        self.assertEqual(d1['text'], 'WETDRY-1')
        self.assertEqual(d1['array'].shape, d1_expected.shape)
        self.assertTrue((d1['array'] == d1_expected).all())
        self.assertEqual(r.lineno, 8)
        # Data Number 2
        d2_shape = (2, 12)
        d2_expected = np.ones(d2_shape)
        d2_expected[1, 2] = 9
        d2 = r.get_array(2, d2_shape, 'i', return_dict=True)
        self.assertEqual(d2['locat'], 11)
        self.assertEqual(d2['cnstnt'], '1')
        self.assertEqual(d2['fmtin'], '(12I2)')
        self.assertEqual(d2['iprn'], '3')
        self.assertFalse(hasattr(d2, 'text'))
        self.assertEqual(d2['array'].shape, d2_expected.shape)
        self.assertTrue((d2['array'] == d2_expected).all())
        self.assertEqual(r.lineno, 11)
        # Data Number 3
        d3_shape = (2, 13)
        d3_expected = np.array(2 * [[-1] + [1] * 11 + [-1]], 'i')
        d3a = np.empty(d3_shape, 'i')
        for ilay in range(d3_shape[0]):
            d3 = r.get_array(3, d3_shape[1], 'i', return_dict=True)
            self.assertEqual(d3['locat'], 11)
            self.assertEqual(d3['fmtin'], '(13I3)')
            self.assertEqual(d3['iprn'], '')
            self.assertTrue(d3['text'].startswith('IBOUND'))
            d3a[ilay, :] = d3['array']
        self.assertEqual(d3['text'], 'IBOUND        L2')
        self.assertEqual(d3a.shape, d3_expected.shape)
        self.assertTrue((d3a == d3_expected).all())
        self.assertEqual(r.lineno, 15)
        # Data Number 4
        d4_shape = (4, 8)
        d4_expected = np.ones(d4_shape, 'f') * 6
        d4 = r.get_array(4, d4_shape, 'f', return_dict=True)
        self.assertEqual(d4['locat'], 0)
        self.assertEqual(d4['cnstnt'], '6.')
        self.assertEqual(d4['fmtin'], '(15F4.0)')
        self.assertEqual(d4['iprn'], '7')
        self.assertEqual(d4['text'], 'Some text')
        self.assertEqual(d4['array'].shape, d4_expected.shape)
        self.assertTrue((d4['array'] == d4_expected).all())
        self.assertEqual(r.lineno, 16)
        # Data Number 5
        d5_shape = (7, 6)
        d5_expected = np.ones(d5_shape) * 8
        d5 = r.get_array(5, d5_shape, 'i', return_dict=True)
        self.assertEqual(d5['locat'], 0)
        self.assertEqual(d5['cnstnt'], '8')
        self.assertEqual(d5['fmtin'], '(12I2)')
        self.assertEqual(d5['iprn'], '3')
        self.assertFalse(hasattr(d5, 'text'))
        self.assertEqual(d5['array'].shape, d5_expected.shape)
        self.assertTrue((d5['array'] == d5_expected).all())
        self.assertEqual(r.lineno, 17)
        # Data Number 6
        d6_shape = (4, 7)
        d6 = r.get_array(6, d6_shape, 'f', return_dict=True)
        self.assertEqual(d6['locat'], -17)
        self.assertEqual(d6['cnstnt'], '1.')
        self.assertEqual(d6['fmtin'], '(BINARY)')
        self.assertEqual(d6['iprn'], '7')
        self.assertFalse(hasattr(d6, 'text'))
        self.assertEqual(d6['array'].shape, d6_expected.shape)
        self.assertTrue((d6['array'] == d6_expected).all())
        self.assertEqual(r.lineno, 18)
        # Data Number 7
        d7_shape = (2, 17, 17)
        d7_expected = np.zeros(d7_shape, 'i')
        d7_expected[0, 6:11, 6:11] = 1
        d7_expected[1, 7:10, 7:10] = 1
        d7a = np.empty(d7_shape, 'i')
        for ilay in range(d7_shape[0]):
            d7 = r.get_array(7, d7_shape[1:], 'i', return_dict=True)
            self.assertEqual(d7['locat'], 16)
            self.assertEqual(d7['fmtin'], '(24I3)')
            self.assertEqual(d7['iprn'], '3')
            self.assertFalse(hasattr(d7, 'text'))
            d7a[ilay, :] = d7['array']
        self.assertEqual(d7a.shape, d7_expected.shape)
        self.assertTrue((d7a == d7_expected).all())
        self.assertEqual(r.lineno, 20)
        # Data Number 8
        d8_shape = (2, 3)
        d8_expected = 145.0 * np.ones(d8_shape, 'f')
        d8 = r.get_array(8, d8_shape, 'f', return_dict=True)
        self.assertEqual(d8['locat'], 0)
        self.assertEqual(d8['cnstnt'], '145.')
        self.assertFalse(hasattr(d8, 'fmtin'))
        self.assertFalse(hasattr(d8, 'iprn'))
        self.assertEqual(d8['array'].shape, d8_expected.shape)
        self.assertTrue((d8['array'] == d8_expected).all())
        self.assertEqual(r.lineno, 21)
        self.assertFalse(r.not_eof)


mf2kdir = '../MODFLOW-2000/data'
mf2005kdir = '../MODFLOW-2005/test-run'
mfnwtdir = '../MODFLOW-NWT/data'
mfusgdir = '../MODFLOW-USG/test'
gmsdir = '/opt/aquaveo/gms/10.0'


class TestMF(unittest.TestCase):

    def test_basic_modflow(self):
        # build Modflow object
        m = mf.Modflow()
        self.assertEqual(len(m), 0)
        self.assertEqual(list(m), [])
        m.dis = mf.DIS()
        self.assertEqual(len(m), 1)
        self.assertEqual(list(m), ['dis'])
        m.append(mf.BAS6())
        self.assertEqual(len(m), 2)
        self.assertEqual(list(m), ['dis', 'bas6'])
        self.assertTrue(isinstance(m.bas6, mf.BAS6))
        del m.dis
        self.assertEqual(len(m), 1)
        self.assertEqual(list(m), ['bas6'])
        self.assertTrue(isinstance(m.bas6, mf.BAS6))
        m.bas6 = mf.BAS6()
        self.assertRaises(ValueError, m.append, True)
        self.assertRaises(AttributeError, setattr, m, 'rch', mf.RIV())
        m.append(mf.DIS())
        self.assertEqual(len(m), 2)
        self.assertEqual(list(m), ['bas6', 'dis'])

    @unittest.skipIf(not os.path.isdir(mf2kdir), 'could not find ' + mf2kdir)
    def test_modflow_2000(self):
        #print(mf2kdir)
        for nam in glob(os.path.join(mf2kdir, '*.nam')):
            #print(nam)
            m = mf.Modflow()
            m.read(nam)
            #print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    @unittest.skipIf(not os.path.isdir(mf2005kdir),
                     'could not find ' + mf2005kdir)
    def test_modflow_2005(self):
        #print(mf2005kdir)
        for nam in glob(os.path.join(mf2005kdir, '*.nam')):
            m = mf.Modflow()
            m.read(nam)
            #print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    @unittest.skipIf(not os.path.isdir(mfnwtdir), 'could not find ' + mfnwtdir)
    def test_modflow_nwt(self):
        #print(mfnwtdir)
        for dirpath, dirnames, filenames in os.walk(mfnwtdir):
            for nam in glob(os.path.join(dirpath, '*.nam')):
                if 'SWI_data_files' in dirpath or 'SWR_data_files' in dirpath:
                    ref_dir = dirpath  # normal
                else:
                    ref_dir = mfnwtdir
                m = mf.Modflow()
                m.read(nam, ref_dir=ref_dir)
                #print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    @unittest.skipIf(not os.path.isdir(mfusgdir), 'could not find ' + mfusgdir)
    def test_modflow_usg(self):
        # print(mfusgdir)
        for dirpath, dirnames, filenames in os.walk(mfusgdir):
            for nam in glob(os.path.join(dirpath, '*.nam')):
                m = mf.Modflow()
                m.read(nam)
                #print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    @unittest.skipIf(not os.path.isdir(gmsdir), 'could not find ' + gmsdir)
    def test_modflow_gms(self):
        # print(gmsdir)
        for dirpath, dirnames, filenames in os.walk(gmsdir):
            for mfn in glob(os.path.join(dirpath, '*.mfn')):
                m = mf.Modflow()
                m.read(mfn)
                #print('%s: %s' % (os.path.basename(mfn), ', '.join(list(m))))


def test_suite():
    return unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestMFPackage),
        unittest.TestLoader().loadTestsFromTestCase(TestMF),
    ])

if __name__ == '__main__':
    unittest.main(verbosity=2)
