#!/usr/bin/env python

import sys
from setuptools import setup

import moflow

if sys.version_info[0:2] < (2, 6):
    sys.exit('Requires Python 2.6 or later')


setup_data = {
    'name': 'moflow',
    'description': 'A Python package for MODFLOW and related programs',
    'version': moflow.__version__,
    'author': moflow.__author__,
    'author_email': moflow.__email__,
    'license': 'BSD',
    'packages': ['moflow'],
    'setup_requires': ['pytest-runner'],
    'tests_require': ['pytest'],
    'zip_safe': True,
}

setup(**setup_data)
