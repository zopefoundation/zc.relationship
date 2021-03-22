##############################################################################
#
# Copyright (c) 2006-2008 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
from setuptools import find_packages
from setuptools import setup

import os


def read(path):
    """Read the contents of a file system path."""
    with open(os.path.join(*path.split('/'))) as f:
        return f.read()


setup(
    name="zc.relationship",
    version='2.1',
    packages=find_packages('src'),
    include_package_data=True,
    package_dir={'': 'src'},
    namespace_packages=['zc'],
    zip_safe=False,
    author='Gary Poster',
    author_email='gary@zope.com',
    description="Zope 3 relationship index.  Precursor to zc.relation.",
    url="https://github.com/zopefoundation/zc.relationship",
    long_description="\n\n".join([
        read('src/zc/relationship/README.rst'),
        read('src/zc/relationship/container.rst'),
        read('CHANGES.rst'),
    ]),
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'License :: OSI Approved :: Zope Public License',
    ],
    license='ZPL 2.1',
    keywords="zope zope3",
    install_requires=[
        'ZODB3 >= 3.8dev',
        'zope.app.container',  # would be nice to remove this
        'zope.app.intid',
        'zope.interface',
        'zope.component',
        'zope.app.keyreference',
        'zope.location',
        'zope.index',
        'zc.relation >= 1.1',
        'zope.app.testing',
        'zope.app.component',
        'zope.testing',
        'six',
        'setuptools',
    ],
    extras_require=dict(
        test=[
            'zope.app.folder',
        ]),
)
