##############################################################################
#
# Copyright (c) 2006-2008 Zope Corporation and Contributors.
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
from setuptools import setup, find_packages

long_description=(
    open('src/zc/relationship/README.txt').read() + '\n\n' +
    open("src/zc/relationship/CHANGES.txt").read())

f = open('TEST_THIS_REST_BEFORE_REGISTERING.txt', 'w')
f.write(long_description)
f.close()

setup(
    name="zc.relationship",
    version="2.0",
    packages=find_packages('src'),
    include_package_data=True,
    package_dir= {'':'src'},
    
    namespace_packages=['zc'],

    zip_safe=False,
    author='Gary Poster',
    author_email='gary@zope.com',
    description=open("README.txt").read(),
    long_description=long_description,
    license='ZPL 2.1',
    keywords="zope zope3",
    install_requires=[
        'ZODB3 >= 3.8dev',
        'zope.app.container', # would be nice to remove this
        'zope.app.intid',
        'zope.interface',
        'zope.component',
        'zope.app.keyreference',
        'zope.location',
        'zope.index',
        'zc.relation',
        
        'zope.app.testing',
        'zope.app.component',
        'zope.testing',
        'setuptools',
        ],
    )
