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
from zope.app.container.interfaces import IReadContainer
import zope.index.interfaces

class ITransitiveQueriesFactory(interface.Interface):
    def __call__(relchain, query, index, cache):
        """return iterable of queries to search further from given relchain.
        last relationship token in relchain is the most recent.
        query is original query that started the search."""

class IFilter(interface.Interface):
    def __call__(relchain, query, index, cache):
        """return boolean: whether to accept the given relchain.
        last relationship token in relchain is the most recent.
        query is original query that started the search.
        Used for the filter and targetFilter arguments of the IIndex query
        methods.  Cache is a dictionary that will be used throughout a given
        search."""

class IIndex(zope.index.interfaces.IInjection,
             zope.index.interfaces.IIndexSearch,
             zope.index.interfaces.IStatistics):

    defaultTransitiveQueriesFactory = interface.Attribute(
        '''the standard way for the index to determine transitive queries.
        Must implement ITransitiveQueriesFactory, or be None''')

    def tokenizeQuery(query):
        '''Given a dictionary of {indexName: object} returns a dictionary of
        {indexname: token} appropriate for the search methods'''

    def getTokensForRelationshipName(reltoken, name):
        "return BTree set or None... XXX"

    def findRelationshipChains(query, maxDepth=None, filter=None,
                               targetQuery=None, targetFilter=None,
                               transitiveQueriesFactory=None):
        """find tuples of relationship tokens for searchTerms.
        - query is a dictionary of {indexName: token}
        - targetQuery is an optional query that specifies that only results
        from relationships that match the targetQuery should be returned.  It
        represents a useful subset of the jobs that can be done with the
        targetFilter.
        - maxDepth is None or a positive integer that specifies maximum depth
        for transitive results.  None means that the transitiveMap will be
        followed until a cycle is detected.  It is a ValueError to provide a
        non-None depth if transitiveQueriesFactory is None and
        index.defaultTransitiveQueriesFactory is None.
        - transitiveFilter is a an optional callable providing
        ITransitiveFilter
        - targetFilter is an optional callable providing targetFilter
        - optional transitiveQueriesFactory takes the place of the index's
        defaultTransitiveQueriesFactory
        
        The algorithm for using the arguments is this:
        - find relationships that match query
        - for each one,
          * if the filter is defined and rejects the relationship,
            continue loop to next relationship (skipping the rest, below).
          * if there is a transitiveQueriesFactory for this query or for the
            index, iterate the queries.  For each query, get the relationships
            that match it.  If any of the query's relationships repeat a query
            earlier in the chain, remember the search as generating a cycle.
            Otherwise, if current depth <= max depth, remember the
            results.  After all the relationships have been processed, add the
            list to the TODO list (the stack) for the process.
          * if the targetQuery is None or matches the current relationship, and
            the targetFilter is None or accepts this relationship, yield
            a tuple if there were no cycles, or an ICircularRelationshipPath
            otherwise.
          (Continue working on TODO stack)
        """

    def isLinked(query, maxDepth=None, filter=None, targetQuery=None,
                 targetFilter=None, transitiveQueriesFactory=None):
        """boolean if there is any result for the given search.
        
        Same arguments as findRelationshipChains.
        
        The general algorithm for using the arguments is this:
        try to yield a single chain from findRelationshipChains with the
        given arguments.  If one can be found, return True, else False."""

    def findValues(resultName, query, maxDepth=None, filter=None,
                   targetQuery=None, targetFilter=None,
                   transitiveQueriesFactory=None):
        """find token results for searchTerms.
        - resultName is the index name wanted for results.
        Otherwise, same arguments as findRelationshipChains.
        
        The general algorithm for using the arguments is this:
        - find relationships that match query
        - for each one,
          * if the filter is defined and rejects the relationship, or if the
            relationship has been seen before, continue loop to next
            relationship (skipping the rest, below).
          * if the targetQuery is None or matches the current relationship, and
            the targetFilter is None or accepts this relationship, find all the
            results for the current relationship.  For each one that hasn't
            been seen before, yield it.
          * if there is a transitiveQueriesFactory for this query or for the
            index, and current depth <= max depth, iterate the queries.
            For each query, if it hasn't been seen before, get the
            relationships that match it, and add them to the TODO list.
        """

class IOptimizingIndex(IIndex):

    deactivateSets = interface.Attribute(
        '''bool: optimization setting.
        controls if _p_deactivate is called after sets have been used.''')
        
    deactivateRels = interface.Attribute(
        '''bool: optimization setting.
        controls if _p_deactivate is called after relationship objects have
        been used.''')

class IRelationship(interface.Interface):
    """An asymmetric relationship."""

    __parent__ = interface.Attribute(
        """The relationship container of which this relationship is a member
        """)

    sources = interface.Attribute(
        """Objects pointing in the relationship.  Readonly.""")

    targets = interface.Attribute(
        """Objects being pointed to in the relationship.  Readonly.""")

class IMutableRelationship(IRelationship):
    """An asymmetric relationship.  Sources and targets can be changed."""

class ISourceRelationship(IRelationship):

    source = interface.Attribute(
        """the source for this object.  Mutable""")

class ITargetRelationship(IRelationship):

    source = interface.Attribute(
        """the source for this object.  Mutable""")

class IOneToOneRelationship(ISourceRelationship, ITargetRelationship):
    pass

class IOneToManyRelationship(ISourceRelationship):
    pass

class IManyToOneRelationship(ITargetRelationship):
    pass

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

    def isLinked(source=None, target=None, maxDepth=1, filter=None):
        """given source, target, or both, return True if a link exists.
        
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
