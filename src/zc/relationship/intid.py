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
"""intid-based containers

$Id$
"""
from zope import interface, component
from BTrees import IOBTree, OOBTree, OIBTree, IIBTree

from zope.app.intid.interfaces import IIntIds

from zc.relationship import interfaces, shared

def generateToken(obj, index, cache, **kwargs):
    intids = cache.get('intids')
    if intids is None:
        intids = cache['intids'] = component.getUtility(
            IIntIds, context=index)
    if 'default' not in kwargs:
        return intids.register(obj)
    else:
        return intids.queryId(obj, kwargs['default'])

def resolveToken(token, index, cache, **kwargs):
    intids = cache.get('intids')
    if intids is None:
        intids = cache['intids'] = component.getUtility(
            IIntIds, context=index)
    if 'default' not in kwargs:
        return intids.getObject(token)
    else:
        return intids.queryObject(token, kwargs['default'])

def Container():
    res = shared.Container(
        generateToken, resolveToken, generateToken, resolveToken)
    interface.alsoProvides(res, interfaces.IIntIdRelationshipContainer)
    return res

try:
    import zc.listcontainer
except ImportError:
    pass
else:
    def ListContainer():
        res = shared.ListContainer(
            generateToken, resolveToken, generateToken, resolveToken)
        interface.alsoProvides(res, interfaces.IIntIdListRelationshipContainer)
        return res
