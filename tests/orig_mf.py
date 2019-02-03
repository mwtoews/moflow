import logging
import os
import numpy as np
import sys

from glob import glob
from textwrap import dedent

from moflow import logger
from moflow.mf import Modflow
from moflow.base import MFPackage
from moflow.pkg.reader import MFFileReader

if sys.version_info[0] < 3:
    from io import BytesIO
    StringIO = BytesIO
else:
    from io import StringIO, BytesIO

try:
    from moflow import pkg
except ImportError:
    os.chdir('..')
    sys.path.append('.')
    from moflow import pkg

try:
    import h5py
except ImportError:
    h5py = None


# logger.level = logging.DEBUG
# logger.level = logging.INFO
logger.level = logging.WARN
# logger.level = logging.ERROR


class TestPackage(MFPackage):
    par1 = None
    par2 = None




class TestMF(unittest.TestCase):

    def test_basic_modflow(self):
        # build Modflow object
        m = Modflow()
        self.assertEqual(len(m), 0)
        self.assertEqual(list(m), [])
        m.dis = pkg.class_dict['DIS']()
        self.assertEqual(len(m), 1)
        self.assertEqual(list(m), ['dis'])
        m.append(pkg.class_dict['BAS6']())
        self.assertEqual(len(m), 2)
        self.assertEqual(list(m), ['dis', 'bas6'])
        self.assertTrue(isinstance(m.bas6, pkg.class_dict['BAS6']))
        del m.dis
        self.assertEqual(len(m), 1)
        self.assertEqual(list(m), ['bas6'])
        self.assertTrue(isinstance(m.bas6, pkg.class_dict['BAS6']))
        m.bas6 = pkg.class_dict['BAS6']()
        self.assertRaises(ValueError, m.append, True)
        self.assertRaises(AttributeError, setattr, m, 'rch', pkg.RIV())
        m.append(pkg.class_dict['DIS']())
        self.assertEqual(len(m), 2)
        self.assertEqual(list(m), ['bas6', 'dis'])

    @unittest.skipIf(not os.path.isdir(mf2kdir), 'could not find ' + mf2kdir)
    def test_modflow_2000(self):
        # print(mf2kdir)
        for nam in glob(os.path.join(mf2kdir, '*.nam')):
            # print(nam)
            m = Modflow()
            m.read(nam)
            # print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    @unittest.skipIf(not os.path.isdir(mf2005kdir),
                     'could not find ' + mf2005kdir)
    def test_modflow_2005(self):
        # print(mf2005kdir)
        for nam in glob(os.path.join(mf2005kdir, '*.nam')):
            m = Modflow()
            m.read(nam)
            # print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    @unittest.skipIf(not os.path.isdir(mfnwtdir), 'could not find ' + mfnwtdir)
    def test_modflow_nwt(self):
        # print(mfnwtdir)
        for dirpath, dirnames, filenames in os.walk(mfnwtdir):
            for nam in glob(os.path.join(dirpath, '*.nam')):
                if 'SWI_data_files' in dirpath or 'SWR_data_files' in dirpath:
                    ref_dir = dirpath  # normal
                else:
                    ref_dir = mfnwtdir
                m = Modflow()
                m.read(nam, ref_dir=ref_dir)
                # print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    @unittest.skipIf(not os.path.isdir(mfusgdir), 'could not find ' + mfusgdir)
    def test_modflow_usg(self):
        # print(mfusgdir)
        for dirpath, dirnames, filenames in os.walk(mfusgdir):
            for nam in glob(os.path.join(dirpath, '*.nam')):
                m = Modflow()
                m.read(nam)
                # print('%s: %s' % (os.path.basename(nam), ', '.join(list(m))))

    @unittest.skipIf(not h5py or not os.path.isdir(gmsdir),
                     'h5py is not installed or could not find ' + gmsdir)
    def test_modflow_gms(self):
        for dirpath, dirnames, filenames in os.walk(gmsdir):
            for mfn in glob(os.path.join(dirpath, '*.mfn')):
                # print(mfn)
                try:
                    m = Modflow()
                    m.read(mfn)
                except IOError:
                    continue


def test_suite():
    return unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestMFPackage),
        unittest.TestLoader().loadTestsFromTestCase(TestMF),
    ])

if __name__ == '__main__':
    unittest.main(verbosity=2)
