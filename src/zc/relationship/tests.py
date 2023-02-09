##############################################################################
#
# Copyright (c) 2004 Zope Foundation and Contributors.
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
import doctest
import unittest

import persistent
# these are used by setup
import transaction
import zope.app.component.hooks
import zope.interface.interfaces
import zope.location.interfaces
import zope.testing.module
from persistent.interfaces import IPersistent
from ZODB.interfaces import IConnection
from ZODB.MappingStorage import DB
from zope import component
from zope.app.component.site import LocalSiteManager
from zope.app.component.site import SiteManagerAdapter
from zope.app.folder import rootFolder
from zope.app.intid import IntIds
from zope.app.intid.interfaces import IIntIds
from zope.app.keyreference.persistent import KeyReferenceToPersistent
from zope.app.keyreference.persistent import connectionOfPersistent
from zope.app.testing import placelesssetup

from zc.relationship import intid
from zc.relationship import keyref
from zc.relationship import shared


class Demo(persistent.Persistent):
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.id)


def keyrefSetUp(test):
    placelesssetup.setUp()
    component.provideAdapter(KeyReferenceToPersistent, adapts=(IPersistent,))
    component.provideAdapter(
        SiteManagerAdapter,
        (zope.location.interfaces.ILocation,),
        zope.interface.interfaces.IComponentLookup)
    component.provideAdapter(
        connectionOfPersistent,
        adapts=(IPersistent,),
        provides=IConnection)
    test.globs['db'] = db = DB()
    test.globs['conn'] = conn = db.open()
    test.globs['root'] = root = conn.root()
    test.globs['app'] = app = root['app'] = rootFolder()
    app.setSiteManager(LocalSiteManager(app))
    zope.app.component.hooks.setSite(app)
    zope.app.component.hooks.setHooks()
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
    sm['intids'] = IntIds()
    registry = zope.interface.interfaces.IComponentRegistry(sm)
    registry.registerUtility(sm['intids'], IIntIds)
    transaction.commit()
    test.globs['Container'] = intid.Container
    test.globs['Relationship'] = shared.Relationship


def tearDown(test):
    zope.app.component.hooks.resetHooks()
    zope.app.component.hooks.setSite()
    transaction.abort()
    test.globs['db'].close()
    placelesssetup.tearDown()


def READMESetUp(test):
    intidSetUp(test)
    zope.testing.module.setUp(test, 'zc.relationship.README')


def READMETearDown(test):
    tearDown(test)
    zope.testing.module.tearDown(test)


def test_suite():
    res = unittest.TestSuite((
        doctest.DocFileSuite(
            'README.rst',
            setUp=READMESetUp, tearDown=READMETearDown,
        ),
        doctest.DocFileSuite(  # keyrefSetUp
            'container.rst', setUp=keyrefSetUp, tearDown=tearDown,
            optionflags=doctest.ELLIPSIS),
        doctest.DocFileSuite(  # intidSetUp
            'container.rst', setUp=intidSetUp, tearDown=tearDown,
            optionflags=doctest.ELLIPSIS),
    ))
    return res
