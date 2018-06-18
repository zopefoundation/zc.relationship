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
"""Relationship interfaces

$Id$
"""
from zope import interface
from zope.app.container.interfaces import IReadContainer
import zope.index.interfaces
import zc.relation.interfaces

ICircularRelationshipPath = zc.relation.interfaces.ICircularRelationPath


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

    def index(relationship):
        """obtains the token for the relationship and indexes (calls
        IInjection.index_doc)"""

    def unindex(relationship):
        """obtains the token for the relationship and unindexes (calls
        IInjection.unindex_doc)"""

    def __contains__(relationship):
        """returns whether the relationship is in the index"""

    def findValueTokens(resultName, query=None, maxDepth=None, filter=None,
                        targetQuery=None, targetFilter=None,
                        transitiveQueriesFactory=None):
        """find token results for searchTerms.
        - resultName is the index name wanted for results.
        - if query is None (or evaluates to boolean False), returns the
          underlying btree data structure; which is an iterable result but
          can also be used with BTree operations
        Otherwise, same arguments as findRelationshipChains.
        """

    def findValues(resultName, query=None, maxDepth=None, filter=None,
                   targetQuery=None, targetFilter=None,
                   transitiveQueriesFactory=None):
        """Like findValueTokens, but resolves value tokens"""

    def findRelationshipTokenChains(query, maxDepth=None, filter=None,
                                    targetQuery=None, targetFilter=None,
                                    transitiveQueriesFactory=None):
        """find tuples of relationship tokens for searchTerms.
        - query is a dictionary of {indexName: token}
        - maxDepth is None or a positive integer that specifies maximum depth
          for transitive results.  None means that the transitiveMap will be
          followed until a cycle is detected.  It is a ValueError to provide a
          non-None depth if transitiveQueriesFactory is None and
          index.defaultTransitiveQueriesFactory is None.
        - filter is a an optional callable providing IFilter that determines
          whether relationships will be traversed at all.
        - targetQuery is an optional query that specifies that only paths with
          final relationships that match the targetQuery should be returned.
          It represents a useful subset of the jobs that can be done with the
          targetFilter.
        - targetFilter is an optional callable providing IFilter that
          determines whether a given path will be included in results (it will
          still be traversed)
        - optional transitiveQueriesFactory takes the place of the index's
          defaultTransitiveQueriesFactory
        """

    def findRelationshipChains(query, maxDepth=None, filter=None,
                               targetQuery=None, targetFilter=None,
                               transitiveQueriesFactory=None):
        "Like findRelationshipTokenChains, but resolves relationship tokens"

    def isLinked(query, maxDepth=None, filter=None, targetQuery=None,
                 targetFilter=None, transitiveQueriesFactory=None):
        """boolean if there is any result for the given search.

        Same arguments as findRelationshipChains.

        The general algorithm for using the arguments is this:
        try to yield a single chain from findRelationshipTokenChains with the
        given arguments.  If one can be found, return True, else False."""

    def tokenizeQuery(query):
        '''Given a dictionary of {indexName: value} returns a dictionary of
        {indexname: token} appropriate for the search methods'''

    def resolveQuery(query):
        '''Given a dictionary of {indexName: token} returns a dictionary of
        {indexname: value}'''

    def tokenizeValues(values, name):
        """Returns an iterable of tokens for the values of the given index
        name"""

    def resolveValueTokens(tokens, name):
        """Returns an iterable of values for the tokens of the given index
        name"""

    def tokenizeRelationship(rel):
        """Returns a token for the given relationship"""

    def resolveRelationshipToken(token):
        """Returns a relationship for the given token"""

    def tokenizeRelationships(rels):
        """Returns an iterable of tokens for the relations given"""

    def resolveRelationshipTokens(tokens):
        """Returns an iterable of relations for the tokens given"""

    def findRelationshipTokenSet(query):
        """Given a single dictionary of {indexName: token}, return a set (based
        on the btree family for relationships in the index) of relationship
        tokens that match it.  Intransitive."""

    def findRelationships(query):
        """Given a single dictionary of {indexName: token}, return an iterable
        of relationships that match the query intransitively"""

    def findValueTokenSet(reltoken, name):
        """Given a relationship token and a value name, return a set (based on
        the btree family for the value) of value tokens for that relationship.
        """


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


class ISourceRelationship(IMutableRelationship):

    source = interface.Attribute(
        """the source for this object.  Mutable""")


class ITargetRelationship(IMutableRelationship):

    target = interface.Attribute(
        """the target for this object.  Mutable""")


class IOneToOneRelationship(ISourceRelationship, ITargetRelationship):
    pass


class IOneToManyRelationship(ISourceRelationship):
    pass


class IManyToOneRelationship(ITargetRelationship):
    pass


class IBidirectionalRelationshipIndex(interface.Interface):

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


class IRelationshipContainer(IReadContainer, IBidirectionalRelationshipIndex):

    def add(object):
        """Add a relationship to the container"""

    def remove(object):
        """Remove a relationship from the container"""


class IKeyReferenceRelationshipContainer(IRelationshipContainer):
    """holds relationships of objects that can be adapted to IKeyReference.

    tokens are key references.
    """


class IIntIdRelationshipContainer(IRelationshipContainer):
    """relationships and the objects they relate must have/be given an intid.

    tokens are intids.
    """


try:
    import zc.listcontainer.interfaces
except ImportError:
    pass
else:
    class IRelationshipListContainer(
            zc.listcontainer.interfaces.IListContainer,
            IBidirectionalRelationshipIndex):
        """Uses the list container API to manage the relationships"""

    class IIntIdRelationshipListContainer(IRelationshipListContainer):
        """tokens are intids"""
