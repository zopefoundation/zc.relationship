import persistent
import persistent.interfaces
from BTrees import OOBTree, IFBTree, IOBTree, Length

from zope import interface, component
import zope.interface.interfaces
from zope.app.intid.interfaces import IIntIds
import zope.app.container.contained

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
            for r in index.findValueTokenSet(relchain[-1], dynamic[1]):
                res = {dynamic[0]: r}
                res.update(static)
                yield res

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

def getModuleTools(module):
    return dict(
        (nm, getattr(module, nm, None)) for nm in 
        ('BTree', 'TreeSet', 'Bucket', 'Set',
         'intersection', 'multiunion', 'union', 'difference'))

class Index(persistent.Persistent, zope.app.container.contained.Contained):
    interface.implements(interfaces.IIndex)

    def _deactivate(self, ob):
        if (getattr(ob, '_p_jar', None) is not None and
            persistent.interfaces.IPersistent.providedBy(ob)):
            ob._p_deactivate()

    def __init__(self, attrs, defaultTransitiveQueriesFactory=None,
                 dumpRel=generateToken, loadRel=resolveToken,
                 relFamily=IFBTree, deactivateSets=False):
        self._name_TO_mapping = OOBTree.BTree()
        # held mappings are objtoken to (relcount, relset)
        self._EMPTY_name_TO_relcount_relset = OOBTree.BTree()
        self._reltoken_name_TO_objtokenset = OOBTree.BTree()
        self.defaultTransitiveQueriesFactory = defaultTransitiveQueriesFactory
        self._relTools = getModuleTools(relFamily)
        self._relTools['load'] = loadRel
        self._relTools['dump'] = dumpRel
        self._relLength = Length.Length()
        self._relTokens = self._relTools['TreeSet']()
        self.deactivateSets = deactivateSets
        self._attrs = _attrs = {} # this is private, and it's not expected to
        # mutate after this initial setting.
        seen = set()
        for data in attrs:
            # see README.txt for description of attrs.
            if zope.interface.interfaces.IElement.providedBy(data):
                data = {'element': data}
            res = getModuleTools(data.get('btree', IFBTree))
            res['element'] = val = data['element']
            res['attrname'] = val.__name__
            res['name'] = data.get('name', res['attrname'])
            if res['name'] in _attrs or val in seen:
                raise ValueError('Duplicate in attrs', res['name'], val)
            seen.add(val)
            _attrs[res['name']] = res
            res['dump'] = data.get('dump', generateToken)
            res['load'] = data.get('load', resolveToken)
            if (res['dump'] is None) ^ (res['load'] is None):
                raise ValueError(
                    "either both of 'dump' and 'load' must be None, or neither")
                # when both load and dump are None, this is a small
                # optimization that can be a large optimization if the returned
                # value is one of the main four options of the selected btree
                # family (BTree, TreeSet, Set, Bucket).
            res['interface'] = val.interface
            res['multiple'] = data.get('multiple', False)
            res['call'] = zope.interface.interfaces.IMethod.providedBy(val)
            if res['TreeSet'].__name__.startswith('I'):
                Mapping = IOBTree.BTree
            else:
                assert res['TreeSet'].__name__.startswith('O')
                Mapping = OOBTree.BTree
            self._name_TO_mapping[res['name']] = Mapping()
            # these are objtoken to (relcount, relset)

    def _getValuesAndTokens(self, rel, data):
        valueSource = data['interface'](rel, None)
        if valueSource is not None:
            values = getattr(valueSource, data['attrname'])
            if data['call']:
                values = values()
            if not data['multiple'] and values is not None:
                # None is a marker for no value
                values = (values,)
            elif not values:
                values = None
        else:
            values = None
        if values is None:
            return values, values, False
        elif data['dump'] is None and isinstance(values, (
            data['TreeSet'], data['BTree'], data['Bucket'], data['Set'])):
            # this is the optimization story (see _add)
            return values, values, True
        else:
            cache = {}
            if data['dump'] is None:
                tokens = data['TreeSet'](values)
            else:
                tokens = data['TreeSet'](
                    data['dump'](o, self, cache) for o in values)
            return values, tokens, False

    def _add(self, relToken, tokens, name, fullTokens):
        self._reltoken_name_TO_objtokenset[(relToken, name)] = fullTokens
        if tokens is None:
            dataset = self._EMPTY_name_TO_relcount_relset
            keys = (name,)
        else:
            dataset = self._name_TO_mapping[name]
            keys = tokens
        for key in keys:
            data = dataset.get(key)
            if data is None:
                data = dataset[key] = (
                    Length.Length(), self._relTools['TreeSet']())
            res = data[1].insert(relToken)
            assert res, 'Internal error: relToken existed in data'
            data[0].change(1)

    def _remove(self, relToken, tokens, name):
        if tokens is None:
            dataset = self._EMPTY_name_TO_relcount_relset
            keys = (name,)
        else:
            dataset = self._name_TO_mapping[name]
            keys = tokens
        for key in keys:
            data = dataset[key]
            data[1].remove(relToken)
            data[0].change(-1)
            if not data[0].value:
                del dataset[key]
            else:
                assert data[0].value > 0

    def index(self, rel):
        self.index_doc(self._relTools['dump'](rel, self, {}), rel)

    def index_doc(self, relToken, rel):
        if relToken in self._relTokens:
            # reindex
            for data in self._attrs.values():
                values, newTokens, optimization = self._getValuesAndTokens(
                    rel, data)
                oldTokens = self._reltoken_name_TO_objtokenset[
                    (relToken, data['name'])]
                if newTokens != oldTokens:
                    if newTokens is not None and oldTokens is not None:
                        added = data['difference'](newTokens, oldTokens)
                        removed = data['difference'](oldTokens, newTokens)
                        if optimization:
                            # the goal of this optimization is to not have to
                            # recreate a TreeSet (which can be large and
                            # relatively timeconsuming) when only small changes
                            # have been made.  We ballpark this by saying
                            # "if there are only a few removals, do them, and
                            # then do an update: it's almost certainly a win
                            # over essentially generating a new TreeSet and
                            # updating it with *all* values.  On the other
                            # hand, if there are a lot of removals, it's
                            # probably quicker just to make a new one."  We
                            # pick >25 removals, mostly arbitrarily, as our 
                            # "cut bait" cue.  We don't just do a len of
                            # removed because lens of btrees are potentially
                            # expensive.
                            for ix, t in enumerate(removed):
                                if ix >= 25: # arbitrary cut-off
                                    newTokens = data['TreeSet'](newTokens)
                                    break
                                oldTokens.remove(t)
                            else:
                                oldTokens.update(added)
                                newTokens = oldTokens
                    else:
                        removed = oldTokens
                        added = newTokens
                        if optimization:
                            newTokens = data['TreeSet'](newTokens)
                    self._remove(relToken, removed, data['name'])
                    self._add(relToken, added, data['name'], newTokens)
        else:
            # new
            for data in self._attrs.values():
                assert self._reltoken_name_TO_objtokenset.get(
                    (relToken, data['name']), self) is self
                values, tokens, gen = self._getValuesAndTokens(rel, data)
                if gen:
                    tokens = data['TreeSet'](tokens)
                self._add(relToken, tokens, data['name'], tokens)
            self._relTokens.insert(relToken)
            self._relLength.change(1)

    def unindex(self, rel):
        self.unindex_doc(self._relTools['dump'](rel, self, {}))

    def __contains__(self, rel):
        return self.tokenizeRelationship(rel) in self._relTokens   

    def unindex_doc(self, relToken):
        if relToken in self._relTokens:
            for data in self._attrs.values():
                tokens = self._reltoken_name_TO_objtokenset.pop(
                    (relToken, data['name']))
                self._remove(relToken, tokens, data['name'])
            self._relTokens.remove(relToken)
            self._relLength.change(-1)

    def documentCount(self):
        return self._relLength.value

    def wordCount(self):
        return 0 # we don't index words; we could arbitrarily keep track of
        # how many related objects we have, but that would be annoying to get
        # right for very questionable benefit

    def clear(self):
        for v in self._name_TO_mapping.values():
            v.clear()
        self._EMPTY_name_TO_relcount_relset.clear()
        self._reltoken_name_TO_objtokenset.clear()
        self._relTokens.clear()
        self._relLength.set(0)

    def apply(self, query):
        # there are two kinds of queries: values and relationships.
        if len(query) != 1:
            raise ValueError('one key in the primary query dictionary')
        (searchType, query) = query.items()[0]
        if searchType=='relationships':
            if self._relTools['TreeSet'] is not IFBTree.TreeSet:
                raise ValueError(
                    'cannot fulfill `apply` interface because cannot return '
                    'an IFBTree-based result')
            res = self._relData(query)
            if res is None:
                res = self._relTools['TreeSet']()
            return res
        elif searchType=='values':
            data = self._attrs[query['resultName']]
            if data['TreeSet'] is not IFBTree.TreeSet:
                raise ValueError(
                    'cannot fulfill `apply` interface because cannot return '
                    'an IFBTree-based result')
            iterable = self._yieldValueTokens(
                query['resultName'], *(self._parse(
                    query['query'], query.get('maxDepth'),
                    query.get('filter'), query.get('targetQuery'),
                    query.get('targetFilter'),
                    query.get('transitiveQueriesFactory')) +
                (True,)))
            if data['multiunion'] is not None:
                res = data['multiunion'](tuple(iterable))
            else:
                res = data['TreeSet']()
                for s in iterable:
                    res = data['union'](res, s)
            return res
        else:
            raise ValueError('unknown query type', searchType)

    def tokenizeQuery(self, query):
        res = {}
        for k, v in query.items():
            data = self._attrs[k]
            if v is not None and data['dump'] is not None:
                v = data['dump'](v, self, {})
            res[k] = v
        return res

    def resolveQuery(self, query):
        res = {}
        for k, v in query.items():
            data = self._attrs[k]
            if v is not None and data['load'] is not None:
                v = data['load'](v, self, {})
            res[k] = v
        return res

    def tokenizeValues(self, values, name):
        dump = self._attrs[name]['dump']
        if dump is None:
            return values
        cache = {}
        return (dump(v, self, cache) for v in values)

    def resolveValueTokens(self, tokens, name):
        load = self._attrs[name]['load']
        if load is None:
            return tokens
        cache = {}
        return (load(t, self, cache) for t in tokens)

    def tokenizeRelationship(self, rel):
        return self._relTools['dump'](rel, self, {})

    def resolveRelationshipToken(self, token):
        return self._relTools['load'](token, self, {})

    def tokenizeRelationships(self, rels):
        cache = {}
        return (self._relTools['dump'](r, self, cache) for r in rels)

    def resolveRelationshipTokens(self, tokens):
        cache = {}
        return (self._relTools['load'](t, self, cache) for t in tokens)

    def findRelationships(self, query):
        return self.resolveRelationshipTokens(
            self.findRelationshipTokenSet(query))

    def findRelationshipTokenSet(self, query):
        res = self._relData(query)
        if res is None:
            res = self._relTools['TreeSet']()
        return res

    def findValueTokenSet(self, reltoken, name):
        res = self._reltoken_name_TO_objtokenset.get((reltoken, name))
        if res is None:
            res = self._attrs[name]['TreeSet']()
        return res

    def _relData(self, searchTerms):
        data = []
        if getattr(searchTerms, 'items', None) is not None:
            searchTerms = searchTerms.items()
        for nm, token in searchTerms:
            if token is None:
                relData = self._EMPTY_name_TO_relcount_relset.get(nm)
            else:
                relData = self._name_TO_mapping[nm].get(token)
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
                intersection = self._relTools['TreeSet'](
                    i for i in first_set if i in second_set)
            else:
                intersection = self._relTools['intersection'](
                    first_set, second_set)
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
        checkTargetFilter = None
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
        getQueries = None
        if transitiveQueriesFactory is None:
            transitiveQueriesFactory = self.defaultTransitiveQueriesFactory
        if transitiveQueriesFactory is None:
            if maxDepth != 1 and maxDepth is not None:
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

    def findValueTokens(self, resultName, query, maxDepth=None, filter=None,
                        targetQuery=None, targetFilter=None,
                        transitiveQueriesFactory=None):
        if resultName not in self._attrs:
            raise ValueError('name not indexed', resultName)
        return self._yieldValueTokens(
            resultName, *self._parse(
                query, maxDepth, filter, targetQuery, targetFilter,
                transitiveQueriesFactory))

    def findValues(self, resultName, query, maxDepth=None, filter=None,
                   targetQuery=None, targetFilter=None,
                   transitiveQueriesFactory=None):
        resolve = self._attrs[resultName]['load']
        if resolve is None:
            return self._yieldValueTokens(
                resultName, *self._parse(
                    query, maxDepth, filter, targetQuery, targetFilter,
                    transitiveQueriesFactory))
        return self._yieldValues(
            resultName, *self._parse(
                query, maxDepth, filter, targetQuery, targetFilter,
                transitiveQueriesFactory))

    def _yieldValues(self, resultName, query, relData, maxDepth, checkFilter,
                     checkTargetFilter, getQueries):
        resolve = self._attrs[resultName]['load']
        cache = {}
        for t in self._yieldValueTokens(resultName, query, relData, maxDepth,
                                        checkFilter, checkTargetFilter,
                                        getQueries):
            yield resolve(t, self, cache)

    def _yieldValueTokens(
        self, resultName, query, relData, maxDepth, checkFilter,
        checkTargetFilter, getQueries, yieldSets=False):
        relSeen = set()
        objSeen = set()
        for path in self._yieldRelationshipTokenChains(
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
        if self._relTools['load'] is None:
            raise RuntimeError('not configured to resolve relationship tokens')
        return self._yieldRelationshipChains(*self._parse(
            query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory))

    def _yieldRelationshipChains(self, query, relData, maxDepth, checkFilter,
                                 checkTargetFilter, getQueries,
                                 findCycles=True):
        resolve = self._relTools['load']
        cache = {}
        for p in self._yieldRelationshipTokenChains(
            query, relData, maxDepth, checkFilter, checkTargetFilter,
            getQueries, findCycles):
            t = (resolve(t, self, cache) for t in p)
            if interfaces.ICircularRelationshipPath.providedBy(p):
                res = CircularRelationshipPath(t, p.cycled)
            else:
                res = tuple(t)
            yield res

    def findRelationshipTokenChains(self, query, maxDepth=None, filter=None,
                                    targetQuery=None, targetFilter=None,
                                    transitiveQueriesFactory=None):
        """find relationship tokens that match the searchTerms.
        
        same arguments as findValueTokens except no resultName.
        """
        return self._yieldRelationshipTokenChains(*self._parse(
            query, maxDepth, filter, targetQuery, targetFilter,
            transitiveQueriesFactory))

    def _yieldRelationshipTokenChains(self, query, relData, maxDepth,
                                      checkFilter, checkTargetFilter,
                                      getQueries, findCycles=True):
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
            self._yieldRelationshipTokenChains(*self._parse(
                query, maxDepth, filter, targetQuery, targetFilter,
                transitiveQueriesFactory)+(False,)).next()
        except StopIteration:
            return False
        else:
            return True
