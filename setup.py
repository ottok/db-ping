#!/usr/bin/env python3

import sys, os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if not sys.version_info[0] == 3:
    sys.exit("Python 2.x is not supported; Python 3.x is required.")

setup(
    name="db_ping",
    version="0.1",
    description="Identify servers running various SSL VPNs",
    long_description=open("README.md").read(),
    long_description_content_type='text/markdown',
    author="Otto Kekäläinen",
    author_email="otto@kekalainen.net",
    license='AGPL-3.0',
    install_requires=open("requirements.txt").read().splitlines(),
    url="https://github.com/ottok/db-ping",
    packages = ['db_ping'],
    entry_points={ 'console_scripts': [ 'db-ping=db_ping.__main__' ] },
)
