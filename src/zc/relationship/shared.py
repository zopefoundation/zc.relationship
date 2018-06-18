##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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
import six

import persistent
from zope import interface
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

try:
    apply
except NameError:
    # PY3
    def apply(func, *args, **kw):
        return func(*args, **kw)


@interface.implementer(interfaces.IRelationship)
class ImmutableRelationship(RelationshipBase):

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


@interface.implementer(interfaces.IMutableRelationship)
class Relationship(ImmutableRelationship):

    @apply
    def sources():
        def get(self):
            return self._sources

        def set(self, value):
            self._sources = tuple(value)
            if interfaces.IBidirectionalRelationshipIndex.providedBy(
                    self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

    @apply
    def targets():
        def get(self):
            return self._targets

        def set(self, value):
            self._targets = tuple(value)
            if interfaces.IBidirectionalRelationshipIndex.providedBy(
                    self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

# some small conveniences; maybe overkill, but I wanted some for a client
# package.


@interface.implementer(interfaces.IOneToOneRelationship)
class OneToOneRelationship(ImmutableRelationship):

    def __init__(self, source, target):
        super(OneToOneRelationship, self).__init__((source,), (target,))

    @apply
    def source():
        def get(self):
            return self._sources[0]

        def set(self, value):
            self._sources = (value,)
            if interfaces.IBidirectionalRelationshipIndex.providedBy(
                    self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

    @apply
    def target():
        def get(self):
            return self._targets[0]

        def set(self, value):
            self._targets = (value,)
            if interfaces.IBidirectionalRelationshipIndex.providedBy(
                    self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)


@interface.implementer(interfaces.IOneToManyRelationship)
class OneToManyRelationship(ImmutableRelationship):

    def __init__(self, source, targets):
        super(OneToManyRelationship, self).__init__((source,), targets)

    @apply
    def source():
        def get(self):
            return self._sources[0]

        def set(self, value):
            self._sources = (value,)
            if interfaces.IBidirectionalRelationshipIndex.providedBy(
                    self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

    @apply
    def targets():
        def get(self):
            return self._targets

        def set(self, value):
            self._targets = tuple(value)
            if interfaces.IBidirectionalRelationshipIndex.providedBy(
                    self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)


@interface.implementer(interfaces.IManyToOneRelationship)
class ManyToOneRelationship(ImmutableRelationship):

    def __init__(self, sources, target):
        super(ManyToOneRelationship, self).__init__(sources, (target,))

    @apply
    def sources():
        def get(self):
            return self._sources

        def set(self, value):
            self._sources = tuple(value)
            if interfaces.IBidirectionalRelationshipIndex.providedBy(
                    self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

    @apply
    def target():
        def get(self):
            return self._targets[0]

        def set(self, value):
            self._targets = (value,)
            if interfaces.IBidirectionalRelationshipIndex.providedBy(
                    self.__parent__):
                self.__parent__.reindex(self)
        return property(get, set)

##############################################################################


class ResolvingFilter(object):
    def __init__(self, filter, container):
        self.filter = filter
        self.container = container

    def __call__(self, relchain, query, index, cache):
        obj = self.container.relationIndex.resolveRelationshipToken(
            relchain[-1])
        return self.filter(obj)


def minDepthFilter(depth):
    if depth is None:
        return None
    if not isinstance(depth, six.integer_types) or depth < 1:
        raise ValueError('invalid minDepth', depth)
    return lambda relchain, query, index, cache: len(relchain) >= depth


class AbstractContainer(persistent.Persistent):
    def __init__(self,
                 dumpSource=None, loadSource=None, sourceFamily=None,
                 dumpTarget=None, loadTarget=None, targetFamily=None,
                 **kwargs):
        source = {'element': interfaces.IRelationship['sources'],
                  'name': 'source', 'multiple': True}
        target = {'element': interfaces.IRelationship['targets'],
                  'name': 'target', 'multiple': True}
        if dumpSource is not None:
            target['dump'] = source['dump'] = dumpSource
        if loadSource is not None:
            target['load'] = source['load'] = loadSource
        if sourceFamily is not None:
            target['btree'] = source['btree'] = sourceFamily
        if dumpTarget is not None:
            target['dump'] = dumpTarget
        if loadTarget is not None:
            target['load'] = loadTarget
        if targetFamily is not None:
            target['btree'] = targetFamily

        ix = index.Index(
            (source, target),
            index.TransposingTransitiveQueriesFactory('source', 'target'),
            **kwargs)
        self.relationIndex = ix
        ix.__parent__ = self

    def reindex(self, object):
        assert object.__parent__ is self
        self.relationIndex.index(object)

    def findTargets(self, source, maxDepth=1, minDepth=None, filter=None):
        return self.relationIndex.findValues(
            'target', self.relationIndex.tokenizeQuery({'source': source}),
            maxDepth, filter and ResolvingFilter(filter, self),
            targetFilter=minDepthFilter(minDepth))

    def findSources(self, target, maxDepth=1, minDepth=None, filter=None):
        return self.relationIndex.findValues(
            'source', self.relationIndex.tokenizeQuery({'target': target}),
            maxDepth, filter and ResolvingFilter(filter, self),
            targetFilter=minDepthFilter(minDepth))

    def findTargetTokens(self, source, maxDepth=1, minDepth=None, filter=None):
        return self.relationIndex.findValueTokens(
            'target', self.relationIndex.tokenizeQuery({'source': source}),
            maxDepth, filter and ResolvingFilter(filter, self),
            targetFilter=minDepthFilter(minDepth))

    def findSourceTokens(self, target, maxDepth=1, minDepth=None, filter=None):
        return self.relationIndex.findValueTokens(
            'source', self.relationIndex.tokenizeQuery({'target': target}),
            maxDepth, filter and ResolvingFilter(filter, self),
            targetFilter=minDepthFilter(minDepth))

    def isLinked(self, source=None, target=None, maxDepth=1, minDepth=None,
                 filter=None):
        tokenize = self.relationIndex.tokenizeQuery
        if source is not None:
            if target is not None:
                targetQuery = tokenize({'target': target})
            else:
                targetQuery = None
            return self.relationIndex.isLinked(
                tokenize({'source': source}),
                maxDepth, filter and ResolvingFilter(filter, self),
                targetQuery,
                targetFilter=minDepthFilter(minDepth))
        elif target is not None:
            return self.relationIndex.isLinked(
                tokenize({'target': target}),
                maxDepth, filter and ResolvingFilter(filter, self),
                targetFilter=minDepthFilter(minDepth))
        else:
            raise ValueError(
                'at least one of `source` and `target` must be provided')

    def _reverse(self, iterable):
        for i in iterable:
            if interfaces.ICircularRelationshipPath.providedBy(i):
                yield index.CircularRelationshipPath(
                    reversed(i),
                    [self.relationIndex.resolveQuery(d) for d in i.cycled])
            else:
                yield tuple(reversed(i))

    def _forward(self, iterable):
        for i in iterable:
            if interfaces.ICircularRelationshipPath.providedBy(i):
                yield index.CircularRelationshipPath(
                    i,
                    [self.relationIndex.resolveQuery(d) for d in i.cycled])
            else:
                yield i

    def findRelationshipTokens(self, source=None, target=None, maxDepth=1,
                               minDepth=None, filter=None):
        tokenize = self.relationIndex.tokenizeQuery
        if source is not None:
            if target is not None:
                targetQuery = tokenize({'target': target})
            else:
                targetQuery = None
            res = self.relationIndex.findRelationshipTokenChains(
                tokenize({'source': source}),
                maxDepth, filter and ResolvingFilter(filter, self),
                targetQuery,
                targetFilter=minDepthFilter(minDepth))
            return self._forward(res)
        elif target is not None:
            res = self.relationIndex.findRelationshipTokenChains(
                tokenize({'target': target}),
                maxDepth, filter and ResolvingFilter(filter, self),
                targetFilter=minDepthFilter(minDepth))
            return self._reverse(res)
        else:
            raise ValueError(
                'at least one of `source` and `target` must be provided')

    def _resolveRelationshipChains(self, iterable):
        for i in iterable:
            chain = tuple(self.relationIndex.resolveRelationshipTokens(i))
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
            30))  # somewhat less than 64 ** 30 variations (64*63*...*35)
    # end subclass API

    def add(self, object):
        key = self._generate_id(object)
        while key in self._SampleContainer__data:
            key = self._generate_id(object)
        super(AbstractContainer, self).__setitem__(key, object)
        self.relationIndex.index(object)

    def remove(self, object):
        key = object.__name__
        if self[key] is not object:
            raise ValueError("Relationship is not stored as its __name__")
        self.relationIndex.unindex(object)
        super(AbstractContainer, self).__delitem__(key)

    @property
    def __setitem__(self):
        raise AttributeError
    __delitem__ = __setitem__
