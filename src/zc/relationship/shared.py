##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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
"""Relationship shared code

$Id$
"""
import random

import persistent
from zope import interface, component
import zope.app.container.contained
import zope.app.container.btree

from zc.relationship import interfaces, index

##############################################################################
# some useful relationship variants
#

try:
    import zc.listcontainer
except ImportError:
    class RelationshipBase(
        persistent.Persistent, zope.app.container.contained.Contained):
        pass
else:
    class RelationshipBase(
        persistent.Persistent,
        zope.app.container.contained.Contained,
        zc.listcontainer.Contained):
        pass

class ImmutableRelationship(RelationshipBase):
    interface.implements(interfaces.IRelationship)
    
    _marker = __name__ = __parent__ = None

    def __init__(self, sources, targets):
        self._sources = tuple(sources)
        self._targets = tuple(targets)

    @property
    def sources(self):
        return self._sources

    @property
    def targets(self):
        return self._targets

    def __repr__(self):
        return '<Relationship from %r to %r>' % (self.sources, self.targets)

class Relationship(ImmutableRelationship):
    interface.implements(interfaces.IMutableRelationship)

    @apply
    def sources():
        def get(self):
            return self._sources
        def set(self, value):
            self._sources = tuple(value)
            if interfaces.IRelationshipContainer.providedBy(self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

    @apply
    def targets():
        def get(self):
            return self._targets
        def set(self, value):
            self._targets = tuple(value)
            if interfaces.IRelationshipContainer.providedBy(self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

# some small conveniences; maybe overkill, but I wanted some for a client
# package.

class OneToOneRelationship(ImmutableRelationship):
    interface.implements(interfaces.IOneToOneRelationship)

    def __init__(self, source, target):
        super(OneToOneRelationship, self).__init__((source,), (target,))

    @apply
    def source():
        def get(self):
            return self._sources[0]
        def set(self, value):
            self._sources = (value,)
            if interfaces.IRelationshipContainer.providedBy(self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

    @apply
    def target():
        def get(self):
            return self._sources[0]
        def set(self, value):
            self._sources = (value,)
            import pdb; pdb.set_trace()
            if interfaces.IRelationshipContainer.providedBy(self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

class OneToManyRelationship(ImmutableRelationship):
    interface.implements(interfaces.IOneToManyRelationship)

    def __init__(self, source, targets):
        super(OneToOneRelationship, self).__init__((source,), targets)

    @apply
    def source():
        def get(self):
            return self._sources[0]
        def set(self, value):
            self._sources = (value,)
            if interfaces.IRelationshipContainer.providedBy(self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

    @apply
    def targets():
        def get(self):
            return self._targets
        def set(self, value):
            self._targets = tuple(value)
            if interfaces.IRelationshipContainer.providedBy(self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

class ManyToOneRelationship(ImmutableRelationship):
    interface.implements(interfaces.IManyToOneRelationship)

    def __init__(self, sources, target):
        super(OneToOneRelationship, self).__init__(sources, (target,))

    @apply
    def sources():
        def get(self):
            return self._sources
        def set(self, value):
            self._sources = tuple(value)
            if interfaces.IRelationshipContainer.providedBy(self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

    @apply
    def target():
        def get(self):
            return self._targets[0]
        def set(self, value):
            self._targets = (value,)
            if interfaces.IRelationshipContainer.providedBy(self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

##############################################################################

class ResolvingFilter(object):
    def __init__(self, filter, container):
        self.filter = filter
        self.container = container

    def __call__(self, relchain, query, index, cache):
        obj = self.container.resolveRelToken(relchain[-1], index, cache)
        return self.filter(obj)

def minDepthFilter(depth):
    if depth is None:
        return None
    if not isinstance(depth, (int, long)) or depth < 1:
        raise ValueError('invalid minDepth', depth)
    return lambda relchain, query, index, cache: len(relchain) >= minDepth

class AbstractContainer(persistent.Persistent):
    def __init__(self,
        generateObjToken, resolveObjToken, generateRelToken, resolveRelToken,
        **kwargs):
        ix = index.Index(
            ({'element': interfaces.IRelationship['sources'],
              'name': 'source'},
             {'element': interfaces.IRelationship['targets'],
              'name': 'target'}),
            generateObjToken,
            index.TransposingTransitiveQueriesFactory('source', 'target'),
            **kwargs)
        self.index = ix
        ix.__parent__ = self
        self.resolveObjToken = resolveObjToken
        self.resolveRelToken = resolveRelToken
        self.generateRelToken = generateRelToken

    def reindex(self, object):
        assert object.__parent__ is self
        assert self[object.__name__] is object
        self.index.index_doc(
            self.generateRelToken(object, self.index, {}), object)

    def _resolveObjTokens(self, iterable):
        resolveObjToken = index.partial(
            self.resolveObjToken, index=self.index, cache={})
        for t in iterable:
            yield resolveObjToken(t)

    def findTargets(self, source, maxDepth=1, minDepth=None, filter=None):
        return self._resolveObjTokens(
            self.findTargetTokens(source, maxDepth, minDepth, filter))

    def findSources(self, target, maxDepth=1, minDepth=None, filter=None):
        return self._resolveObjTokens(
            self.findSourceTokens(target, maxDepth, minDepth, filter))

    def findTargetTokens(self, source, maxDepth=1, minDepth=None, filter=None):
        return self.index.findValues(
            'target', self.index.tokenizeQuery({'source': source}),
            maxDepth, filter and ResolvingFilter(filter, self),
            targetFilter=minDepthFilter(minDepth))

    def findSourceTokens(self, target, maxDepth=1, minDepth=None, filter=None):
        return self.index.findValues(
            'source', self.index.tokenizeQuery({'target': target}),
            maxDepth, filter and ResolvingFilter(filter, self),
            targetFilter=minDepthFilter(minDepth))

    def isLinked(self, source=None, target=None, maxDepth=1, minDepth=None,
                 filter=None):
        if source is not None:
            return self.index.isLinked(
                self.index.tokenizeQuery({'source': source}),
                maxDepth, filter and ResolvingFilter(filter, self),
                target and self.index.tokenizeQuery({'target': target}),
                targetFilter=minDepthFilter(minDepth))
        elif target is not None:
            return self.index.isLinked(
                self.index.tokenizeQuery({'target': target}),
                maxDepth, filter and ResolvingFilter(filter, self),
                targetFilter=minDepthFilter(minDepth))
        else:
            raise ValueError(
                'at least one of `source` and `target` must be provided')

    def _reverse(self, iterable):
        for i in iterable:
            if interfaces.ICircularRelationshipPath.providedBy(i):
                yield index.CircularRelationshipPath(reversed(i), i.cycled)
            else:
                yield tuple(reversed(i))

    def findRelationshipTokens(self, source=None, target=None, maxDepth=1,
                               minDepth=None, filter=None):
        if source is not None:
            return self.index.findRelationshipChains(
                self.index.tokenizeQuery({'source': source}),
                maxDepth, filter and ResolvingFilter(filter, self),
                target and self.index.tokenizeQuery({'target': target}),
                targetFilter=minDepthFilter(minDepth))
        elif target is not None:
            res = self.index.findRelationshipChains(
                self.index.tokenizeQuery({'target': target}),
                maxDepth, filter and ResolvingFilter(filter, self),
                targetFilter=minDepthFilter(minDepth))
            return self._reverse(res)
        else:
            raise ValueError(
                'at least one of `source` and `target` must be provided')

    def _resolveRelationshipChains(self, iterable):
        resolveRelToken = index.partial(
            self.resolveRelToken, index=self.index, cache={})
        for i in iterable:
            chain = (resolveRelToken(t) for t in i)
            if interfaces.ICircularRelationshipPath.providedBy(i):
                yield index.CircularRelationshipPath(chain, i.cycled)
            else:
                yield tuple(chain)

    def findRelationships(self, source=None, target=None, maxDepth=1,
                          minDepth=None, filter=None):
        return self._resolveRelationshipChains(
            self.findRelationshipTokens(
                source, target, maxDepth, minDepth, filter))

class Container(AbstractContainer, zope.app.container.btree.BTreeContainer):

    def __init__(self, *args, **kwargs):
        AbstractContainer.__init__(self, *args, **kwargs)
        zope.app.container.btree.BTreeContainer.__init__(self)

    # subclass API
    def _generate_id(self, relationship):
        return ''.join(random.sample(
            "abcdefghijklmnopqrtstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_1234567890",
            30)) # 64 ** 30 variations
    # end subclass API

    def add(self, object):
        key = self._generate_id(object)
        while key in self._SampleContainer__data:
            key = self._generate_id(object)
        super(AbstractContainer, self).__setitem__(key, object)
        self.index.index_doc(
            self.generateRelToken(object, self.index, {}), object)

    def remove(self, object):
        token = self.generateRelToken(object, self.index, {})
        key = object.__name__
        if self[key] is not object:
            raise ValueError("Relationship is not stored as its __name__")
        super(AbstractContainer, self).__delitem__(key)
        self.index.unindex_doc(token)

    @property
    def __setitem__(self):
        raise AttributeError
    __delitem__ = __setitem__

try:
    import zc.listcontainer
except ImportError:
    pass
else:
    class ListContainer(AbstractContainer, zc.listcontainer.ListContainer):

        def __init__(self, *args, **kwargs):
            AbstractContainer.__init__(self, *args, **kwargs)
            zc.listcontainer.ListContainer.__init__(self)
    
        def _after_add(
            self, item, oldSuper, oldPrevious, oldNext, super, previous, next):
            res = super(AbstractListContainer, self)._after_add(
                item, oldSuper, oldPrevious, oldNext, super, previous, next)
            self.index.index_doc(
                self.generateRelToken(item, self.index, {}), item)
            item.__parent__ = self
            return res

        def _after_multi_add(self, items, previous, next, i):
            res = super(AbstractListContainer, self)._after_multi_add(
                items, previous, next, i)
            for item in items:
                self.index.index_doc(
                    self.generateRelToken(item, self.index, {}), item)
                item.__parent__ = self
            return res

        def movereplace(self, i, item):
            try:
                current = self[i]
            except IndexError:
                current = None
            super(AbstractListContainer, self).movereplace(i, item)
            if current is not None and current.super is not self:
                self.index.unindex_doc(
                    self.generateRelToken(item, self.index, {}))

        def pop(self, i=-1):
            try:
                current = self[i]
            except IndexError:
                pass # let the super call raise the right error
            else:
                self.index.unindex_doc(
                    self.generateRelToken(item, self.index, {}))
            super(AbstractListContainer, self).pop(i)

        def __delslice__(self, i, j): # don't support step
            old = self[i:j]
            super(AbstractListContainer, self).__delslice__(i, j)
            if old:
                for item in old:
                    self.index.unindex_doc(
                        self.generateRelToken(item, self.index, {}))

        def silentpop(self, i=-1):
            res = super(AbstractListContainer, self).silentpop(i)
            self.index.unindex_doc(
                self.generateRelToken(item, self.index, {}))
            return res
