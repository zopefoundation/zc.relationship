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
"""keyref-based containers

$Id$
"""
from zope import interface
from BTrees import OOBTree

from zope.app.keyreference.interfaces import IKeyReference

from zc.relationship import interfaces, shared

class Container(shared.AbstractContainer):
    interface.implements(interfaces.IKeyReferenceRelationshipContainer)

    def _index_factory(self):
        return OOBTree.OOBTree()

    def _set_factory(self, *args):
        return OOBTree.OOTreeSet(*args)

    def _set_difference(self, set1, set2):
        return OOBTree.difference(set1, set2)

    def _generate_token(self, ob, cache, **kwargs):
        return IKeyReference(ob)

    def _resolve_token(self, token, cache, **kwargs):
        return token()
