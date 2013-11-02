import os
import sys
from glob import glob
from io import BytesIO
from textwrap import dedent
import unittest

try:
    from moflow import mf
except ImportError:
    os.chdir('..')
    sys.path.append('.')
    from moflow import mf

#import logging
#mf.logger.level = logging.DEBUG
#mf.logger.level = logging.INFO
#mf.logger.level = logging.WARN
#mf.logger.level = logging.ERROR


class TEST(mf._MFPackage):
    par1 = None
    par2 = None


class TestMF(unittest.TestCase):

    def test_mf_reader_basic(self):
        p = TEST()
        p.fpath = BytesIO(dedent('''\
            # A comment
            100 ignore
            200 -2.4E-12
            4 500 FREE
            -44 888.0
            last line
        '''))
        r = mf._MFFileReader(p)
        self.assertTrue(r.not_eof)
        self.assertEqual(r.lineno, 0)
        self.assertEqual(len(r), 6)
        # Data Set 0: Text
        r.read_text()
        self.assertEqual(r.lineno, 1)
        self.assertEqual(p.text, ['A comment'])
        # Data Set 1: an item
        self.assertEqual(r.get_items(1, 1, 'i'), [100])
        self.assertEqual(r.lineno, 2)
        # Data Set 2: two named items
        self.assertRaises(mf.MFReaderError, r.read_named_items,
                          2, ('par1', 'par2'), 'i')
        r.lineno -= 1  # manually scroll back 1 line and try again
        r.read_named_items(2, ('par1', 'par2'), ['i', 'f'])
        self.assertEqual(p.par1, 200)
        self.assertAlmostEqual(p.par2, -2.4E-12)
        # Data Set 3: three named items
        items = r.get_named_items(3, ['a', 'b', 'c'], ['f', 'i', 's'])
        self.assertEqual(items, {'a': 4.0, 'b': 500, 'c': 'FREE'})
        # Data Set 4: two named items
        r.read_named_items(4, ['par1', 'par2'], ['i', 'f'])
        self.assertEqual(p.par1, -44)
        self.assertAlmostEqual(p.par2, 888.0)
        # post-Data Set
        self.assertTrue(r.not_eof)
        self.assertEqual(r.next_line(), 'last line\n')
        self.assertEqual(r.lineno, 6)
        self.assertFalse(r.not_eof)
        # Try to read past EOF
        self.assertRaises(mf.MFReaderError, r.next_line)
        self.assertEqual(r.lineno, 6)

    def test_mf_reader_empty(self):
        p = TEST()
        p.fpath = BytesIO(dedent('''# Empty file'''))
        r = mf._MFFileReader(p)
        self.assertTrue(r.not_eof)
        self.assertEqual(r.lineno, 0)
        self.assertEqual(len(r), 1)
        # Item 0: Text
        r.read_text()
        self.assertEqual(r.lineno, 1)
        self.assertEqual(p.text, ['Empty file'])
        self.assertFalse(r.not_eof)

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

    mf2kdir = '../MODFLOW-2000/data'

    @unittest.skipIf(not os.path.isdir(mf2kdir), 'could not find ' + mf2kdir)
    def test_modflow2000(self):
        print(self.mf2kdir)
        for nam in glob(os.path.join(self.mf2kdir, '*.nam')):
            m = mf.Modflow()
            m.read(nam)
            print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    mf2005kdir = '../MODFLOW-2005/test-run'

    @unittest.skipIf(not os.path.isdir(mf2005kdir),
                     'could not find ' + mf2005kdir)
    def test_modflow2005(self):
        print(self.mf2005kdir)
        for nam in glob(os.path.join(self.mf2005kdir, '*.nam')):
            m = mf.Modflow()
            m.read(nam)
            print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    mfnwtdir = '../MODFLOW-NWT/data'

    @unittest.skipIf(not os.path.isdir(mfnwtdir), 'could not find ' + mfnwtdir)
    def test_modflow_nwt(self):
        print(self.mfnwtdir)
        for dirpath, dirnames, filenames in os.walk(self.mfnwtdir):
            for nam in glob(os.path.join(dirpath, '*.nam')):
                if 'SWI_data_files' in dirpath or 'SWR_data_files' in dirpath:
                    ref_dir = dirpath
                else:
                    ref_dir = self.mfnwtdir
                m = mf.Modflow()
                m.read(nam, ref_dir=ref_dir)
                print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    mfusgdir = '../MODFLOW-USG/test'

    @unittest.skipIf(not os.path.isdir(mfusgdir), 'could not find ' + mfusgdir)
    def test_modflow_usg(self):
        print(self.mfusgdir)
        for dirpath, dirnames, filenames in os.walk(self.mfusgdir):
            for nam in glob(os.path.join(dirpath, '*.nam')):
                m = mf.Modflow()
                m.read(nam)
                print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestMF)

if __name__ == '__main__':
    unittest.main(verbosity=2)
