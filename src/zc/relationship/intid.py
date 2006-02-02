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
from BTrees import IOBTree

from zope.app.intid.interfaces import IIntIds

from zc.relationship import interfaces, shared

class Container(shared.AbstractContainer):
    interface.implements(interfaces.IIntIdRelationshipContainer)

    def _index_factory(self):
        return IOBTree.IOBTree()

    def _set_factory(self, *args):
        return IOBTree.IOTreeSet(*args)

    def _set_difference(self, set1, set2):
        return IOBTree.difference(set1, set2)

    def _generate_token(self, ob, cache, **kwargs):
        intids = cache.get('intids')
        if intids is None:
            intids = cache['intids'] = component.getUtility(
                IIntIds, context=self)
        if 'default' not in kwargs:
            return intids.register(ob)
        else:
            return intids.queryId(ob, kwargs['default'])

    def _resolve_token(self, token, cache, **kwargs):
        intids = cache.get('intids')
        if intids is None:
            intids = cache['intids'] = component.getUtility(
                IIntIds, context=self)
        if 'default' not in kwargs:
            return intids.getObject(token)
        else:
            return intids.queryObject(token, kwargs['default'])
