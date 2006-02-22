##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
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
"""Relationship tests

$Id$
"""
import unittest
from zope.testing import doctest

# these are used by setup
import transaction
import persistent
from persistent.interfaces import IPersistent
from ZODB.interfaces import IConnection
from ZODB.tests.util import DB

from zope import component, interface
import zope.component.interfaces
from zope.component.tests import placelesssetup
from zope.app.keyreference.persistent import (
    KeyReferenceToPersistent, connectionOfPersistent)
from zope.app.folder import rootFolder
import zope.app.utility
from zope.app.component.site import LocalSiteManager, SiteManagerAdapter
from zope.app.intid import IntIds
from zope.app.intid.interfaces import IIntIds
import zope.app.component.interfaces.registration
import zope.app.annotation.interfaces
import zope.app.annotation.attribute

from zc.relationship import intid, keyref, shared

class Demo(persistent.Persistent):
    def __init__(self, id):
        self.id = id
    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.id)

def keyrefSetUp(test):
    placelesssetup.setUp()
    component.provideAdapter(KeyReferenceToPersistent, adapts=(IPersistent,))
    component.provideAdapter(
        SiteManagerAdapter,
        adapts=(None,),
        provides=zope.component.interfaces.ISiteManager)
    component.provideAdapter(
        connectionOfPersistent,
        adapts=(IPersistent,),
        provides=IConnection)
    test.globs['db'] = db = DB()
    test.globs['conn'] = conn = db.open()
    test.globs['root'] = root = conn.root()
    test.globs['app'] = app = root['app'] = rootFolder()
    app.setSiteManager(LocalSiteManager(app))
    for i in range(30):
        id = 'ob%d' % i
        app[id] = Demo(id)
    transaction.commit()
    test.globs['Container'] = keyref.Container
    test.globs['Relationship'] = shared.Relationship

def intidSetUp(test):
    keyrefSetUp(test)
    app = test.globs['app']
    sm = app.getSiteManager()
    package = sm['default']
    package['intids'] = IntIds()
    registration = zope.app.utility.UtilityRegistration(
        '', IIntIds, package['intids'])
    key = package.registrationManager.addRegistration(registration)
    registration.status = (
        zope.app.component.interfaces.registration.ActiveStatus)
    transaction.commit()
    test.globs['Container'] = intid.Container
    test.globs['Relationship'] = shared.Relationship

def tearDown(test):
    transaction.abort()
    test.globs['db'].close()
    placelesssetup.tearDown()

def test_suite():
    return unittest.TestSuite((
        doctest.DocFileSuite(
            'README.txt',
            setUp=placelesssetup.setUp, tearDown=placelesssetup.tearDown),
        doctest.DocFileSuite(
            'container.txt', setUp=keyrefSetUp, tearDown=tearDown),
        doctest.DocFileSuite(
            'container.txt', setUp=intidSetUp, tearDown=tearDown),
        doctest.DocFileSuite(
            'listcontainer.txt', setUp=intidSetUp, tearDown=tearDown),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
