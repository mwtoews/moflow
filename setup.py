#!/usr/bin/env python

import sys
if sys.version_info[0:2] < (2, 6):
    sys.exit('Requires Python 2.6 or later')

from distutils.core import Command, setup
from unittest import TextTestRunner, TestLoader


import mf


class test(Command):
    """Run unit tests after in-place build"""
    description = __doc__
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import tests
        tests = TestLoader().loadTestsFromName('test_suite', tests)
        runner = TextTestRunner(verbosity=2)
        result = runner.run(tests)
        sys.exit(not bool(result.wasSuccessful()))


setup(
    name          = 'moflow',
    packages      = ['mf'],
    version       = mf.__version__,
    cmdclass      = {'test': test},
    description   = 'A Python package for MODFLOW and related programs',
    author        = mf.__author__,
    author_email  = mf.__email__,
    license       = 'BSD',
)
