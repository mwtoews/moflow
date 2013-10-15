from unittest import TestSuite

from . import test_mf


def test_suite():
    suite = TestSuite()
    suite.addTest(test_mf.test_suite())
    return suite
