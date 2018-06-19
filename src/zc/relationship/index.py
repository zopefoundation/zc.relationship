##############################################################################
#
# Copyright (c) 2004-2008 Zope Foundation and Contributors.
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

import persistent
import persistent.interfaces
import BTrees

from zope import interface, component
import zope.interface.interfaces
from zope.app.intid.interfaces import IIntIds
import zope.app.container.contained

from zc.relationship import interfaces

import zc.relation.catalog

# N.B.
# this is now a subclass of the zc.relation.catalog.Catalog.  It only exists
# to provide backwards compatibility.  New work should go in zc.relation.
# Ideally, new code should use the zc.relation code directly.

##############################################################################
# the marker that shows that a path is circular
#

CircularRelationshipPath = zc.relation.catalog.CircularRelationPath

##############################################################################
# a common case transitive queries factory


@interface.implementer(interfaces.ITransitiveQueriesFactory)
class TransposingTransitiveQueriesFactory(persistent.Persistent):

    def __init__(self, name1, name2):
        self.names = [name1, name2]  # a list so we can use index

    def __call__(self, relchain, query, index, cache):
        dynamic = cache.get('dynamic')
        if dynamic is None:
            static = cache['static'] = {}
            dynamic = cache['dynamic'] = []
            for nm, val in query.items():
                try:
                    ix = self.names.index(nm)
                except ValueError:
                    static[nm] = val
                else:
                    if dynamic:
                        # both were specified: no transitive search known.
                        del dynamic[:]
                        break
                    else:
                        dynamic.append(nm)
                        dynamic.append(self.names[not ix])
        else:
            static = cache['static']
        if dynamic:
            name = dynamic[1]
            if name is None:
                rels = (relchain[-1],)
            else:
                rels = index.findValueTokenSet(relchain[-1], name)
            for r in rels:
                res = {dynamic[0]: r}
                res.update(static)
                yield res


def factoryWrapper(factory, query, index):
    cache = {}

    def getQueries(relchain):
        if not relchain:
            return (query,)
        return factory(relchain, query, index, cache)
    return getQueries

##############################################################################
# a common case intid getter and setter


def generateToken(obj, index, cache):
    intids = cache.get('intids')
    if intids is None:
        intids = cache['intids'] = component.getUtility(IIntIds)
    return intids.register(obj)


def resolveToken(token, index, cache):
    intids = cache.get('intids')
    if intids is None:
        intids = cache['intids'] = component.getUtility(IIntIds)
    return intids.getObject(token)

##############################################################################
# the relationship index


@interface.implementer_only(
    interfaces.IIndex, interface.implementedBy(persistent.Persistent),
    interface.implementedBy(zope.app.container.contained.Contained)
)
class Index(zc.relation.catalog.Catalog,
            zope.app.container.contained.Contained):

    def __init__(self, attrs, defaultTransitiveQueriesFactory=None,
                 dumpRel=generateToken, loadRel=resolveToken,
                 relFamily=None, family=None, deactivateSets=False):
        super(Index, self).__init__(dumpRel, loadRel, relFamily, family)
        self.defaultTransitiveQueriesFactory = defaultTransitiveQueriesFactory
        for data in attrs:
            if zope.interface.interfaces.IElement.providedBy(data):
                data = {'element': data}
            if 'callable' in data:
                if 'element' in data:
                    raise ValueError(
                        'cannot provide both callable and element')
                data['element'] = data.pop('callable')
            elif 'element' not in data:
                raise ValueError('must provide element or callable')
            if 'dump' not in data:
                data['dump'] = generateToken
            if 'load' not in data:
                data['load'] = resolveToken
            self.addValueIndex(**data)
        # deactivateSets is now ignored.  It was broken before.

    # disable zc.relation default query factories, enable zc.relationship
    addDefaultQueryFactory = iterDefaultQueryFactories = None
    removeDefaultQueryFactory = None

    def _getQueryFactory(self, query, queryFactory):
        res = None
        if queryFactory is None:
            queryFactory = self.defaultTransitiveQueriesFactory
        if queryFactory is not None:
            res = factoryWrapper(queryFactory, query, self)
        return queryFactory, res

    # disable search indexes
    _iterListeners = zc.relation.catalog.Catalog.iterListeners
    addSearchIndex = iterSearchIndexes = removeSearchIndex = None

    def documentCount(self):
        return self._relLength.value

    def wordCount(self):
        return 0  # we don't index words

    def apply(self, query):
        # there are two kinds of queries: values and relationships.
        if len(query) != 1:
            raise ValueError('one key in the primary query dictionary')
        (searchType, query) = list(query.items())[0]
        if searchType == 'relationships':
            relTools = self.getRelationModuleTools()
            if relTools['TreeSet'].__name__[:2] not in ('IF', 'LF'):
                raise ValueError(
                    'cannot fulfill `apply` interface because cannot return '
                    'an (I|L)FBTree-based result')
            res = self.getRelationTokens(query)
            if res is None:
                res = relTools['TreeSet']()
            return res
        elif searchType == 'values':
            data = self._attrs[query['resultName']]
            if data['TreeSet'].__name__[:2] not in ('IF', 'LF'):
                raise ValueError(
                    'cannot fulfill `apply` interface because cannot return '
                    'an (I|L)FBTree-based result')
            q = BTrees.family32.OO.Bucket(query.get('query', ()))
            targetq = BTrees.family32.OO.Bucket(query.get('targetQuery', ()))
            queryFactory, getQueries = self._getQueryFactory(
                q, query.get('transitiveQueriesFactory'))
            iterable = self._yieldValueTokens(
                query['resultName'], *(self._parse(
                    q, query.get('maxDepth'), query.get('filter'), targetq,
                    query.get('targetFilter'), getQueries) +
                    (True,)))
            # IF and LF have multiunion; can demand its presence
            return data['multiunion'](tuple(iterable))
        else:
            raise ValueError('unknown query type', searchType)

    tokenizeRelationship = zc.relation.catalog.Catalog.tokenizeRelation

    resolveRelationshipToken = (
        zc.relation.catalog.Catalog.resolveRelationToken)

    tokenizeRelationships = zc.relation.catalog.Catalog.tokenizeRelations

    resolveRelationshipTokens = (
        zc.relation.catalog.Catalog.resolveRelationTokens)

    def findRelationshipTokenSet(self, query):
        # equivalent to findRelationshipTokens(query, maxDepth=1)
        res = self._relData(query)
        if res is None:
            res = self._relTools['TreeSet']()
        return res

    def findValueTokenSet(self, reltoken, name):
        # equivalent to findValueTokens(name, {None: reltoken}, maxDepth=1)
        res = self._reltoken_name_TO_objtokenset.get((reltoken, name))
        if res is None:
            res = self._attrs[name]['TreeSet']()
        return res

    def findValueTokens(self, resultName, query=(), maxDepth=None,
                        filter=None, targetQuery=None, targetFilter=None,
                        transitiveQueriesFactory=None, _ignored=None):
        # argument names changed slightly
        if targetQuery is None:
            targetQuery = ()
        return super(Index, self).findValueTokens(
            resultName, query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory, True)

    def findValues(self, resultName, query=(), maxDepth=None, filter=None,
                   targetQuery=None, targetFilter=None,
                   transitiveQueriesFactory=None):
        # argument names changed slightly
        if targetQuery is None:
            targetQuery = ()
        return super(Index, self).findValues(
            resultName, query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory)

    def findRelationships(self, query=(), maxDepth=None, filter=None,
                          targetQuery=None, targetFilter=None,
                          transitiveQueriesFactory=None):
        # argument names changed slightly
        if targetQuery is None:
            targetQuery = ()
        return super(Index, self).findRelations(
            query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory)

    def findRelationshipTokens(self, query=(), maxDepth=None, filter=None,
                               targetQuery=None, targetFilter=None,
                               transitiveQueriesFactory=None, _ignored=None):
        # argument names changed slightly
        if targetQuery is None:
            targetQuery = ()
        return super(Index, self).findRelationTokens(
            query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory, True)

    def findRelationshipTokenChains(self, query=(), maxDepth=None, filter=None,
                                    targetQuery=None, targetFilter=None,
                                    transitiveQueriesFactory=None):
        # argument names changed slightly
        if targetQuery is None:
            targetQuery = ()
        return super(Index, self).findRelationTokenChains(
            query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory)

    def findRelationshipChains(self, query=(), maxDepth=None, filter=None,
                               targetQuery=None, targetFilter=None,
                               transitiveQueriesFactory=None):
        # argument names changed slightly
        if targetQuery is None:
            targetQuery = ()
        return super(Index, self).findRelationChains(
            query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory)

    def isLinked(self, query=(), maxDepth=None, filter=None,
                 targetQuery=None, targetFilter=None,
                 transitiveQueriesFactory=None):
        # argument names changed slightly
        if targetQuery is None:
            targetQuery = ()
        return super(Index, self).canFind(
            query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory)
