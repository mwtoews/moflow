import os
import sys
from glob import glob
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


class TestMF(unittest.TestCase):

    def test_basic_modflow(self):
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
