from setuptools import setup, find_packages

setup(
    name="zc.relationship",
    version="1.1.1",
    packages=find_packages('src'),
    include_package_data=True,
    package_dir= {'':'src'},
    
    namespace_packages=['zc'],

    zip_safe=False,
    author='Zope Project',
    author_email='zope3-dev@zope.org',
    description=open("README.txt").read(),
    long_description=(
        open('CHANGES.txt').read() +
        '\n========\nOverview\n========\n\n' +
        open("src/zc/relationship/README.txt").read()),
    license='ZPL 2.1',
    keywords="zope zope3",
    install_requires=[
        'ZODB3',
        'zope.app.container', # would be nice to remove this
        'zope.app.folder', # would be nice to remove this
        'zope.app.intid',
        'zope.interface',
        'zope.component',
        'zope.app.keyreference',
        'zope.location',
        'zope.index',
        
        'zope.app.testing', # TODO remove this
        'zope.app.component', # TODO remove this
        'zope.testing',
        'setuptools',
        ],
    )
