import os
from glob import glob
import logging
import unittest

import mf

#mf.logger.level = logging.INFO
mf.logger.level = logging.WARN
#mf.logger.level = logging.ERROR


class TestMF(unittest.TestCase):

    def test_modflow2000(self):
        mfdir = '../MODFLOW-2000/data'
        self.assertTrue(os.path.isdir(mfdir))
        for nam in glob(os.path.join(mfdir, '*.nam')):
            print(nam)
            m = mf.Modflow()
            m.read(nam)

    def test_modflow2005(self):
        mfdir = '../MODFLOW-2005/test-run'
        self.assertTrue(os.path.isdir(mfdir))
        for nam in glob(os.path.join(mfdir, '*.nam')):
            print(nam)
            m = mf.Modflow()
            m.read(nam)

    def test_modflow_nwt(self):
        mfdir = '../MODFLOW-NWT/data'
        self.assertTrue(os.path.isdir(mfdir))
        for nam in glob(os.path.join(mfdir, 'Ex_prob1a', '*.nam')):
            print(nam)
            m = mf.Modflow()
            m.read(nam, dir=mfdir)
        for nam in glob(os.path.join(mfdir, 'Ex_prob1b', '*.nam')):
            print(nam)
            m = mf.Modflow()
            m.read(nam, dir=mfdir)
        for nam in glob(os.path.join(mfdir, 'Ex_prob2', '*.nam')):
            print(nam)
            m = mf.Modflow()
            m.read(nam, dir=mfdir)
        for nam in glob(os.path.join(mfdir, 'Ex_prob3', '*.nam')):
            print(nam)
            m = mf.Modflow()
            m.read(nam, dir=mfdir)
        for nam in glob(os.path.join(mfdir, 'Lake_bath_example', '*.nam')):
            print(nam)
            m = mf.Modflow()
            m.read(nam, dir=mfdir)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestMF)

if __name__ == '__main__':
    unittest.main(verbosity=2)
