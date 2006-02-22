import types
try:
    from functional import partial # Py 2.5
except ImportError:
    class partial(object): # from http://www.python.org/peps/pep-0309.html

        def __init__(*args, **kw):
            self = args[0]
            self.fn, self.args, self.kw = (args[1], args[2:], kw)

        def __call__(self, *args, **kw):
            if kw and self.kw:
                d = self.kw.copy()
                d.update(kw)
            else:
                d = kw or self.kw
            return self.fn(*(self.args + args), **d)

import persistent
import persistent.interfaces
from BTrees import OOBTree, IFBTree, Length

from zope import interface
import zope.interface.interfaces
import zope.index.interfaces

from zc.relationship import interfaces

##############################################################################
# the marker that shows that a path is circular
#

class CircularRelationshipPath(tuple):
    interface.implements(interfaces.ICircularRelationshipPath)

    def __new__(kls, elements, cycled):
        res = super(CircularRelationshipPath, kls).__new__(kls, elements)
        res.cycled = cycled
        return res
    def __repr__(self):
        return 'cycle%s' % super(CircularRelationshipPath, self).__repr__()

##############################################################################
# a common case transitive queries factory

class TransposingTransitiveQueriesFactory(persistent.Persistent):
    interface.implements(interfaces.ITransitiveQueriesFactory)

    def __init__(self, name1, name2):
        self.names = [name1, name2] # a list so we can use index

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
            for r in index.getTokensForRelationshipName(relchain[-1],
                                                        dynamic[1], ()):
                res = {dynamic[0]: r}
                res.update(static)
                yield res

##############################################################################
# the relationship index
#

class Index(persistent.Persistent):
    interface.implements(interfaces.IIndex)

    def _deactivate(self, ob):
        if (getattr(ob, '_p_jar', None) is not None and
            persistent.interfaces.IPersistent.providedBy(ob)):
            ob._p_deactivate()

    def __init__(self, attrs, generateObjToken,
                 defaultTransitiveQueriesFactory=None,
                 objSetFactory=IFBTree.IFTreeSet, objDiff=IFBTree.difference,
                 objUnion=IFBTree.union, relSetFactory=IFBTree.IFTreeSet,
                 relIntersection=IFBTree.intersection, relUnion=IFBTree.union,
                 deactivateSets=True):
        self._objtoken_name_TO_relcount_relset = OOBTree.OOBTree()
        self._EMPTY_name_TO_relcount_relset = OOBTree.OOBTree()
        self._reltoken_name_TO_objtokenset = OOBTree.OOBTree()
        self.defaultTransitiveQueriesFactory = defaultTransitiveQueriesFactory
        self._objSetFactory = objSetFactory
        self._relSetFactory = relSetFactory
        self.generateObjToken = generateObjToken
        self._objDiff = objDiff
        self._objUnion = objUnion
        self._relIntersection = relIntersection
        self._relUnion = relUnion
        self._relTokens = relSetFactory()
        self._relLength = Length.Length()
        _attrs = {}
        seen = set()
        for data in attrs:
            val = data['element']
            attrname = val.__name__
            name = data.get('name', attrname)
            iface = val.interface
            multiBool = not data.get('single', False)
            callBool = zope.interface.interfaces.IMethod.providedBy(val)
            if name in _attrs or (iface, attrname) in seen:
                raise ValueError('Duplicate in attrs', name, iface, attrname)
            seen.add((iface, attrname))
            _attrs[name] = (name, iface, attrname, callBool, multiBool)
        self._attrs = _attrs
        self.deactivateSets = deactivateSets

    def _getValuesAndTokens(self, rel, name, generateToken):
        name, iface, attrname, callBool, multiBool = self._attrs[name]
        valueSource = iface(rel, None)
        if valueSource is not None:
            values = getattr(valueSource, attrname)
            if callBool:
                values = values()
            if not multiBool:
                if values is not None: # None is a marker for no value
                    values = (values,)
            elif not values:
                values = None
        else:
            values = None
        if values is None:
            return values, values
        else:
            return values, self._objSetFactory(
                generateToken(o) for o in values)

    def _add(self, relToken, tokens, name, fullTokens):
        self._reltoken_name_TO_objtokenset[(relToken, name)] = fullTokens
        if tokens is None:
            dataset = self._EMPTY_name_TO_relcount_relset
            keys = (name,)
        else:
            dataset = self._objtoken_name_TO_relcount_relset
            keys = ((token, name) for token in tokens)
        for key in keys:
            data = dataset.get(key)
            if data is None:
                data = dataset[key] = (Length.Length(), self._relSetFactory())
            res = data[1].insert(relToken)
            assert res, 'Internal error: relToken existed in data'
            data[0].change(1)

    def _remove(self, relToken, tokens, name):
        if tokens is None:
            dataset = self._EMPTY_name_TO_relcount_relset
            keys = (name,)
        else:
            dataset = self._objtoken_name_TO_relcount_relset
            keys = ((token, name) for token in tokens)
        for key in keys:
            data = dataset[key]
            data[1].remove(relToken)
            data[0].change(-1)
            if not data[0].value:
                del dataset[key]
            else:
                assert data[0].value > 0

    def index_doc(self, relToken, rel):
        generateToken = partial(self.generateObjToken, index=self, cache={})
        if relToken in self._relTokens:
            # reindex
            for name, iface, attrname, callBool, multiBool in (
                self._attrs.values()):
                assert self._reltoken_name_TO_objtokenset.get(
                    (relToken, name), self) is not self, (
                    'relationship not indexed')
                values, newTokens = self._getValuesAndTokens(
                    rel, name, generateToken)
                oldTokens = self._reltoken_name_TO_objtokenset[
                    (relToken, name)]
                if newTokens != oldTokens:
                    if newTokens is not None and oldTokens is not None:
                        added = self._objDiff(newTokens, oldTokens)
                        removed = self._objDiff(oldTokens, newTokens)
                    else:
                        removed = oldTokens
                        added = newTokens
                    self._remove(relToken, removed, name)
                    self._add(relToken, added, name, newTokens)
        else:
            # new
            for name, iface, attrname, callBool, multiBool in (
                self._attrs.values()):
                assert self._reltoken_name_TO_objtokenset.get(
                    (relToken, name), self) is self
                values, tokens = self._getValuesAndTokens(
                    rel, name, generateToken)
                self._add(relToken, tokens, name, tokens)
            self._relTokens.insert(relToken)
            self._relLength.change(1)

    def unindex_doc(self, relToken):
        for name, iface, attrname, callBool, multiBool in self._attrs.values():
            tokens = self._reltoken_name_TO_objtokenset.pop((relToken, name))
            self._remove(relToken, tokens, name)
        self._relTokens.remove(relToken)
        self._relLength.change(-1)

    def documentCount(self):
        return self._relLength.value

    def wordCount(self):
        return 0 # we don't index words; we could arbitrarily keep track of
        # how many related objects we have, but that would be annoying to get
        # right for very questionable benefit

    def clear(self):
        self._reltoken_name_TO_objtokenset.clear()
        self._objtoken_name_TO_relcount_relset.clear()
        self._EMPTY_name_TO_relcount_relset.clear()
        self._relTokens.clear()
        self._relLength.set(0)

    def apply(self, query):
        # there are two kinds of queries: values and relationships.
        if len(query) != 1:
            raise ValueError('one key in the primary query dictionary')
        (searchType, query) = query.items()[0]
        if searchType=='relationships':
            res = self._relData(query)
            if res is None:
                res = self.objSetFactory()
            return res
        elif searchType=='values':
            if query['resultName'] not in self._attrs:
                raise ValueError('name not indexed', nm)
            res = self._objSetFactory()
            for s in  self._yieldValues(
                query['resultName'], *(self._parse(
                    query['query'], query.get('maxDepth'),
                    query.get('filter'), query.get('targetQuery'),
                    query.get('targetFilter'),
                    query.get('transitiveQueriesFactory')) +
                (True,))):
                res = self._objUnion(res, s)
            return res
        else:
            raise ValueError('unknown query type', searchType)

    def tokenizeQuery(self, query):
        generateToken = partial(self.generateObjToken, index=self, cache={})
        res = {}
        for k, v in query.items():
            if k not in self._attrs:
                raise ValueError('name not indexed', k)
            if v is not None:
                v = generateToken(v)
            res[k] = v
        return res

    def findRelationships(self, query):
        generateToken = partial(self.generateObjToken, index=self, cache={})
        res = self._relData(query)
        if res is None:
            res = ()
        return res

    def getTokensForRelationshipName(self, reltoken, name, default=None):
        return self._reltoken_name_TO_objtokenset.get(
            (reltoken, name), default)

    def _relData(self, searchTerms):
        data = []
        if getattr(searchTerms, 'items', None) is not None:
            searchTerms = searchTerms.items()
        for nm, token in searchTerms:
            if token is None:
                relData = self._EMPTY_name_TO_relcount_relset.get(nm)
            else:
                relData = self._objtoken_name_TO_relcount_relset.get(
                    (token, nm))
            if relData is None or relData[0].value == 0:
                return None
            data.append((relData[0].value, nm, token, relData[1]))
        data.sort()
        while len(data) > 1:
            first_count, _ignore1, _ignore2, first_set = data[0]
            second_count, second_name, second_token, second_set = data[1]
            if first_count <= second_count/10:
                # we'll just test this by hand: intended to be an optimization.
                # should be tested and the factor adjusted (or this
                # code path removed, relying only on the standard BTree
                # intersection code).  The theory behind this is that the
                # standard BTree intersection code just iterates over the sets
                # to find matches.  Therefore, if you have one set of 
                # range(100000) and another of (99999,) then it will be fairly
                # inefficient.  walking a BTree to find membership is very
                # cheap, so if the first_count is significantly smaller than
                # the second_count we should just check whether each
                # member of the smaller set is in the larger, one at a time.
                intersection = self._relSetFactory(
                    i for i in first_set if i in second_set)
            else:
                intersection = self._relIntersection(first_set, second_set)
            if self.deactivateSets:
                self._deactivate(first_set)
                self._deactivate(second_set)
            if not intersection:
                return None
            data = data[2:]
            # we can't know how many are in a new set without a possibly
            # expensive len; however, the len should be <= first_count
            data.insert(0, (first_count, None, None, intersection))
        return data[0][3]

    def _parse(self, query, maxDepth, filter, targetQuery, targetFilter,
               transitiveQueriesFactory):
        relData = self._relData(query)
        if maxDepth is not None and (
            not isinstance(maxDepth, (int, long)) or maxDepth < 1):
            raise ValueError('maxDepth must be None or a positive integer')
        if filter is not None:
            filterCache = {}
            def checkFilter(relchain, query):
                return filter(relchain, query, self, filterCache)
        else:
            checkFilter = None
        targetCache = {}
        if targetQuery is not None:
            targetData = self._relData(targetQuery)
            if targetData is None:
                relData = None # shortcut
            else:
                if targetFilter is not None:
                    def checkTargetFilter(relchain, query):
                        return relchain[-1] in targetData and targetFilter(
                            relchain, query, self, targetCache)
                else:
                    def checkTargetFilter(relchain, query):
                        return relchain[-1] in targetData
        elif targetFilter is not None:
            def checkTargetFilter(relchain, query):
                return targetFilter(relchain, query, self, targetCache)
        else:
            checkTargetFilter = None
        getQueries = None
        if transitiveQueriesFactory is None:
            transitiveQueriesFactory = self.defaultTransitiveQueriesFactory
        if transitiveQueriesFactory is None:
            if maxDepth != 1:
                raise ValueError(
                    'if maxDepth != 1, transitiveQueriesFactory must be '
                    'available')
        else:
            transitiveCache = {}
            def getQueries(relchain, query):
                return transitiveQueriesFactory(
                    relchain, query, self, transitiveCache)
        return (query, relData, maxDepth, checkFilter, checkTargetFilter,
                getQueries)

    def findValues(self, resultName, query, maxDepth=None, filter=None,
                   targetQuery=None, targetFilter=None,
                   transitiveQueriesFactory=None):
        if resultName not in self._attrs:
            raise ValueError('name not indexed', nm)
        return self._yieldValues(
            resultName, *self._parse(
                query, maxDepth, filter, targetQuery, targetFilter,
                transitiveQueriesFactory))

    def _yieldValues(self, resultName, query, relData, maxDepth, checkFilter,
                     checkTargetFilter, getQueries, yieldSets=False):
        relSeen = set()
        objSeen = set()
        for path in self._yieldRelationshipChains(
            query, relData, maxDepth, checkFilter, checkTargetFilter,
            getQueries, findCycles=False):
            relToken = path[-1]
            if relToken not in relSeen:
                relSeen.add(relToken)
                outputSet = self._reltoken_name_TO_objtokenset.get(
                    (relToken, resultName))
                if outputSet:
                    if yieldSets:
                        yield outputSet
                    else:
                        for token in outputSet:
                            if token not in objSeen:
                                yield token
                                objSeen.add(token)
                            if self.deactivateSets:
                                self._deactivate(outputSet)

    def findRelationshipChains(self, query, maxDepth=None, filter=None,
                               targetQuery=None, targetFilter=None,
                               transitiveQueriesFactory=None):
        """find relationship tokens that match the searchTerms.
        
        same arguments as findValueTokens except no resultName.
        """
        return self._yieldRelationshipChains(*self._parse(
            query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory))

    def _yieldRelationshipChains(self, query, relData, maxDepth, checkFilter,
                                 checkTargetFilter, getQueries,
                                 findCycles=True):
        if not relData:
            raise StopIteration
        stack = [((), iter(relData))]
        while stack:
            tokenChain, relDataIter = stack[0]
            try:
                relToken = relDataIter.next()
            except StopIteration:
                stack.pop(0)
            else:
                tokenChain += (relToken,)
                if checkFilter is not None and not checkFilter(
                    tokenChain, query):
                    continue
                walkFurther = maxDepth is None or len(tokenChain) < maxDepth
                if getQueries is not None and (walkFurther or findCycles):
                    oldInputs = frozenset(tokenChain)
                    next = set()
                    cycled = []
                    for q in getQueries(tokenChain, query):
                        relData = self._relData(q)
                        if relData:
                            intersection = oldInputs.intersection(relData)
                            if intersection:
                                # it's a cycle
                                cycled.append(q)
                            elif walkFurther:
                                next.update(relData)
                            if self.deactivateSets:
                                self._deactivate(relData)
                    if walkFurther and next:
                        stack.append((tokenChain, iter(next)))
                    if cycled:
                        tokenChain = CircularRelationshipPath(
                            tokenChain, cycled)
                if (checkTargetFilter is None or
                    checkTargetFilter(tokenChain, query)):
                    yield tokenChain

    def isLinked(self, query, maxDepth=None, filter=None,
                 targetQuery=None, targetFilter=None,
                 transitiveQueriesFactory=None):
        try:
            self.findRelationshipChains(
                query, maxDepth, filter, targetQuery, targetFilter,
                transitiveQueriesFactory).next()
        except StopIteration:
            return False
        else:
            return True
