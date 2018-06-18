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
"""keyref-based containers

$Id$
"""
from zope import interface
from BTrees import OOBTree

from zope.app.keyreference.interfaces import IKeyReference

from zc.relationship import interfaces, shared


def generateObjToken(ob, index, cache, **kwargs):
    return IKeyReference(ob)


def resolveObjToken(token, index, cache, **kwargs):
    return token()


def generateRelToken(ob, index, cache, **kwargs):
    return ob.__name__


def resolveRelToken(token, index, cache, **kwargs):
    return index.__parent__[token]


def Container():
    res = shared.Container(
        generateObjToken, resolveObjToken, OOBTree,
        dumpRel=generateRelToken, loadRel=resolveRelToken,
        relFamily=OOBTree)
    interface.alsoProvides(res, interfaces.IKeyReferenceRelationshipContainer)
    return res
