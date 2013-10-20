#!/usr/bin/env python

import sys
if sys.version_info[0:2] < (2, 6):
    sys.exit('Requires Python 2.6 or later')

from distutils.core import Command, setup

import moflow


class test(Command):
    """Run unit tests after in-place build"""
    description = __doc__
    user_options = [
        ('logger=', 'L',
         'logger level: 10 for debug to 50 for critical messages')
    ]

    def initialize_options(self):
        """Set defaults"""
        import logging
        self.logger = logging.WARN

    def finalize_options(self):
        self.dump_options()
        if hasattr(self.logger, 'upper'):
            self.logger = int(self.logger)
        moflow.logger.level = self.logger

    def run(self):
        from unittest import TextTestRunner, TestLoader
        import tests
        tests = TestLoader().loadTestsFromName('test_suite', tests)
        runner = TextTestRunner(verbosity=2)
        result = runner.run(tests)
        sys.exit(not bool(result.wasSuccessful()))

setup_data = {
    'name': 'moflow',
    'packages': ['moflow'],
    'version': moflow.__version__,
    'cmdclass': {'test': test},
    'description': 'A Python package for MODFLOW and related programs',
    'author': moflow.__author__,
    'author_email': moflow.__email__,
    'license': 'BSD',
}
setup(**setup_data)
