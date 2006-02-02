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
"""Relationship interfaces

$Id$
"""
from zope import interface
from zope.app.location.interfaces import ILocation
from zope.app.container.interfaces import IReadContainer

class IRelationship(ILocation):
    """An asymmetric relationship."""

    sources = interface.Attribute(
        """Objects pointing in the relationship.  Readonly.""")

    targets = interface.Attribute(
        """Objects being pointed to in the relationship.  Readonly.""")

class IKeyReferenceRelationship(IRelationship):

    source_references = interface.Attribute(
        """key references to the sources in the relationship""")

    target_references = interface.Attribute(
        """key references to the targets in the relationship""")

class ICircularRelationshipPath(interface.Interface):
    """A tuple that has a circular relationship in the very final element of
    the path."""

    cycled = interface.Attribute(
        """a frozenset of the objects that cycled at the very end of the
        current path""")

class IRelationshipContainer(IReadContainer):

    def add(object):
        """Add a relationship to the container"""

    def remove(object):
        """Remove a relationship from the container"""

    def findTargets(source, maxDepth=1, filter=None):
        """Given a source, iterate over objects to which it points.
        
        maxDepth is the number of relationships through which the search
        should walk transitively.  It must be a positive integer.
        
        filter is an optional callable that takes a relationship and returns
        a boolean True value if it should be included, and a False if not.
        """

    def findSources(target, maxDepth=1, filter=None):
        """Given a target, iterate over objects that point to it.
        
        maxDepth is the number of relationships through which the search
        should walk transitively.  It must be a positive integer.
        
        filter is an optional callable that takes a relationship and returns
        a boolean True value if it should be included, and a False if not.
        """

    def isLinked(source, target, maxDepth=1, filter=None):
        """returns True if source points to target.
        
        maxDepth is the number of relationships through which the search
        should walk transitively.  It must be a positive integer.
        
        filter is an optional callable that takes a relationship and returns
        a boolean True value if it should be included, and a False if not.
        """

    def findRelationships(
        source=None, target=None, maxDepth=1, filter=None):
        """given source, target, or both, iterate over all relationship paths.
        
        maxDepth is the number of relationships through which the search
        should walk transitively.  It must be a positive integer.
        
        filter is an optional callable that takes a relationship and returns
        a boolean True value if it should be included, and a False if not.
        
        If a cycle is found, it is omitted by default.  if includeCycles is
        True, it returns the cycle in an ICircularRelationshipPath and then
        does not continue down the cycle.
        """

    def findTargetTokens(source, maxDepth=1, filter=None):
        """As findTargets, but returns tokens rather than the objects"""

    def findSourceTokens(source, maxDepth=1, filter=None):
        """As findSources, but returns tokens rather than the objects"""

    def findRelationshipTokens(source, maxDepth=1, filter=None):
        """As findRelationships, but returns tokens rather than the objects"""

class IKeyReferenceRelationshipContainer(IRelationshipContainer):
    """holds relationships of objects that can be adapted to IKeyReference.
    
    tokens are key references.
    """

class IIntIdRelationshipContainer(IRelationshipContainer):
    """relationships and the objects they relate must have/be given an intid.
    
    tokens are intids.
    """
