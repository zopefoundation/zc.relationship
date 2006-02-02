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
"""Relationship core code

$Id$
"""
import types
import random
import persistent

from zope import interface, component
import zope.app.container.btree

from zc.relationship import interfaces

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

class Relationship(persistent.Persistent):
    interface.implements(interfaces.IRelationship)
    
    __name__ = __parent__ = None

    def __init__(self, sources, targets):
        self._sources = tuple(sources)
        self._targets = tuple(targets)

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

    def __repr__(self):
        return '<Relationship from %r to %r>' % (self._sources, self._targets)

class CircularRelationshipPath(tuple):
    interface.implements(interfaces.ICircularRelationshipPath)
    def __new__(kls, elements, cycled):
        res = super(CircularRelationshipPath, kls).__new__(kls, elements)
        res.cycled = frozenset(cycled)
        return res
    def __repr__(self):
        return 'cycle%s' % super(CircularRelationshipPath, self).__repr__()

class AbstractContainer(zope.app.container.btree.BTreeContainer):

    # subclassing API

    def _index_factory(self):
        raise NotImplementedError
        # return IOBTree.IOBTree()

    def _set_factory(self, *args):
        raise NotImplementedError
        # return IOBTree.IOTreeSet(*args)

    def _generate_id(self, relationship):
        return ''.join(random.sample(
            "abcdefghijklmnopqrtstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_1234567890",
            30)) # 64 ** 30 variations

    def _deactivate(self, ob):
        if getattr(ob, '_p_jar', None) is not None:
            ob._p_deactivate()

    def _generate_token(self, ob, cache, **kwargs):
        # kwargs may contain a "default" value.  If this is provided and the
        # implementation can only return a token if it has already been made,
        # it should return the default if the token has not already been made.
        raise NotImplementedError

    def _resolve_token(self, token, cache, **kwargs):
        # kwargs may contain a "default" value.  If this is provided and the
        # token does not resolve, return the default value.  If a default is
        # not provided, it should raise a LookupError exception (such as
        # KeyError) if the token does not resolve.
        raise NotImplementedError

    def _set_difference(self, set1, set2):
        raise NotImplementedError
        # return IOBTree.difference(set1, set2)

    # end subclassing API

    interface.implements(interfaces.IRelationshipContainer)

    __parent__ = __name__ = None

    def __init__(self):
        self._src_to_rel = self._index_factory()
        self._rel_to_src = self._index_factory()
        self._rel_to_tgt = self._index_factory()
        self._tgt_to_rel = self._index_factory()
        super(AbstractContainer, self).__init__()

    def add(self, object):
        key = self._generate_id(object)
        while key in self._SampleContainer__data:
            key = self._generate_id(object)
        super(AbstractContainer, self).__setitem__(key, object)
        generate_token = partial(self._generate_token, cache={})
        object_token = generate_token(object)
        for values, rel_to_value, value_to_rel in (
            (object.sources, self._rel_to_src, self._src_to_rel),
            (object.targets, self._rel_to_tgt, self._tgt_to_rel)):
            assert rel_to_value.get(object_token) is None
            tokens = tuple(generate_token(o) for o in values)
            rel_to_value[object_token] = self._set_factory(tokens)
            for token in tokens:
                rel_set = value_to_rel.get(token)
                if rel_set is None:
                    rel_set = value_to_rel[token] = self._set_factory()
                rel_set.insert(object_token)

    def reindex(self, object):
        generate_token = partial(self._generate_token, cache={})
        object_token = generate_token(object)
        for values, rel_to_value, value_to_rel in (
            (object.sources, self._rel_to_src, self._src_to_rel),
            (object.targets, self._rel_to_tgt, self._tgt_to_rel)):
            new_tokens = self._set_factory(
                generate_token(o) for o in values)
            old_tokens = rel_to_value[object_token]
            if new_tokens != old_tokens:
                added = self._set_difference(new_tokens, old_tokens)
                removed = self._set_difference(old_tokens, new_tokens)
                rel_to_value[object_token] = new_tokens
                for token in removed:
                    value_to_rel[token].remove(object_token)
                for token in added:
                    rel_set = value_to_rel.get(token)
                    if rel_set is None:
                        rel_set = value_to_rel[token] = self._set_factory()
                    rel_set.insert(object_token)

    def remove(self, object):
        key = object.__name__
        if self[key] is not object:
            raise ValueError("Relationship is not stored as its __name__")
        super(AbstractContainer, self).__delitem__(key)
        generate_token = partial(self._generate_token, cache={})
        object_token = generate_token(object)
        for values, rel_to_value, value_to_rel in (
            (object.sources, self._rel_to_src, self._src_to_rel),
            (object.targets, self._rel_to_tgt, self._tgt_to_rel)):
            tokens = tuple(generate_token(o) for o in values)
            del rel_to_value[object_token]
            for token in tokens:
                value_to_rel[token].remove(object_token)

    @property
    def __setitem__(self):
        raise AttributeError
    __delitem__ = __setitem__

    def findTargets(self, source, maxDepth=1, filter=None):
        if (not isinstance(maxDepth, (int, types.NoneType)) or
            isinstance(maxDepth, int) and maxDepth < 1):
            raise ValueError('maxDepth must be None or a positive integer')
        return self._find(
            self._src_to_rel, self._rel_to_tgt, source, maxDepth, filter, True)

    def findSources(self, target, maxDepth=1, filter=None):
        if (not isinstance(maxDepth, (int, types.NoneType)) or
            isinstance(maxDepth, int) and maxDepth < 1):
            raise ValueError('maxDepth must be None or a positive integer')
        return self._find(
            self._tgt_to_rel, self._rel_to_src, target, maxDepth, filter, True)

    def findTargetTokens(self, source, maxDepth=1, filter=None):
        if (not isinstance(maxDepth, (int, types.NoneType)) or
            isinstance(maxDepth, int) and maxDepth < 1):
            raise ValueError('maxDepth must be None or a positive integer')
        return self._find(
            self._src_to_rel, self._rel_to_tgt, source, maxDepth, filter,
            False)

    def findSourceTokens(self, target, maxDepth=1, filter=None):
        if (not isinstance(maxDepth, (int, types.NoneType)) or
            isinstance(maxDepth, int) and maxDepth < 1):
            raise ValueError('maxDepth must be None or a positive integer')
        return self._find(
            self._tgt_to_rel, self._rel_to_src, target, maxDepth, filter,
            False)

    def _find(self, rel_index, dest_index, input, maxDepth, filter, resolve):
        cache = {}
        generate_token = partial(self._generate_token, cache=cache)
        resolve_token = partial(self._resolve_token, cache=cache)
        input_token = generate_token(input, default=None)
        if input_token is None:
            raise StopIteration
        rels = rel_index.get(input_token)
        if rels is not None:
            yielded = set()
            seen_rel = set()
            stack = [((input_token,), iter(rels))]
            while stack:
                history, rels = stack[0]
                try:
                    rel = rels.next()
                except StopIteration:
                    stack.pop(0)
                else:
                    if rel in seen_rel:
                        continue
                    seen_rel.add(rel)
                    if filter is None or filter(resolve_token(rel)):
                        len_history = len(history)
                        matches = dest_index[rel]
                        for ref in matches:
                            if ref not in yielded:
                                if resolve:
                                    yield resolve_token(ref)
                                else:
                                    yield ref
                                yielded.add(ref)
                                if maxDepth is None or maxDepth > len_history:
                                    rels = rel_index.get(ref)
                                    if rels is not None:
                                        stack.append(
                                            (history+(ref,), iter(rels)))
                        self._deactivate(matches)

    def isLinked(self, source, target, maxDepth=1, filter=None):
        try:
            iter(self.findRelationships(
                source, target, maxDepth, filter)).next()
        except StopIteration:
            return False
        return True

    def findRelationshipTokens(
        self, source=None, target=None, maxDepth=1, filter=None):
        if source is None and target is None:
            raise ValueError(
                'at least one of `source` and `target` must be provided')
        if (not isinstance(maxDepth, (int, types.NoneType)) or
            isinstance(maxDepth, int) and maxDepth < 1):
            raise ValueError('maxDepth must be None or a positive integer')
        return self._findRelationships(
            source, target, maxDepth, filter, False)

    def findRelationships(
        self, source=None, target=None, maxDepth=1, filter=None):
        if source is None and target is None:
            raise ValueError(
                'at least one of `source` and `target` must be provided')
        if (not isinstance(maxDepth, (int, types.NoneType)) or
            isinstance(maxDepth, int) and maxDepth < 1):
            raise ValueError('maxDepth must be None or a positive integer')
        return self._findRelationships(
            source, target, maxDepth, filter, True)

    def _findRelationships(
        self, source=None, target=None, maxDepth=1, filter=None,
        resolve=False):
        cache = {}
        generate_token = partial(self._generate_token, cache=cache)
        resolve_token = partial(self._resolve_token, cache=cache)
        if source is not None:
            reverse = False
            input = source
            rel_index = self._src_to_rel
            start_index = self._rel_to_src
            dest_index = self._rel_to_tgt
            if target is None:
                match_token = None
            elif isinstance(target, int):
                match_token = target
            else:
                match_token = generate_token(target, default=None)
                if match_token is None:
                    raise StopIteration
        else:
            reverse = True
            input = target
            rel_index = self._tgt_to_rel
            dest_index = self._rel_to_src
            start_index = self._rel_to_tgt
            match_token = None
        input_token = generate_token(input, default=None)
        if input_token is None:
            raise StopIteration
        # now the search proper
        rels = rel_index.get(input_token)
        if rels is not None:
            resolved_rel = new_relationship_chain = None
            stack = [(frozenset(), (), (), iter(rels), rels, set())]
            while stack:
                (old_inputs, relationship_token_chain, relationship_chain,
                 iter_rels, rels, old_seen) = stack[0]
                try:
                    rel = iter_rels.next()
                except StopIteration:
                    self._deactivate(rels)
                    stack.pop(0)
                else:
                    if rel in old_seen or rel in relationship_token_chain:
                        continue
                    old_seen.add(rel)
                    if resolve or filter is not None:
                        resolved_rel = resolve_token(rel)
                        if reverse:
                            new_relationship_chain = (
                                (resolved_rel,) + relationship_chain)
                        else:
                            new_relationship_chain = (
                                relationship_chain + (resolved_rel,))
                    if reverse:
                        new_relationship_token_chain = (
                            rel,) + relationship_token_chain
                    else:
                        new_relationship_token_chain = (
                            relationship_token_chain + (rel,))
                    if filter is None or filter(resolved_rel):
                        len_history = len(new_relationship_token_chain)
                        matches = dest_index[rel]
                        reverse_matches = start_index[rel]
                        new_inputs = old_inputs.union(reverse_matches)
                        self._deactivate(reverse_matches)
                        new_seen = set()
                        cycled = set()
                        for iid in matches:
                            if iid not in new_inputs:
                                if maxDepth is None or maxDepth > len_history:
                                    rels = rel_index.get(iid)
                                    if rels is not None:
                                        stack.append(
                                            (new_inputs,
                                            new_relationship_token_chain,
                                            new_relationship_chain,
                                            iter(rels),
                                            rels,
                                            new_seen))
                            else:
                                cycled.add(iid)
                        if match_token is None or match_token in matches:
                            if resolve:
                                res = new_relationship_chain
                                cycled = set(
                                    resolve_token(iid) for iid in cycled)
                            else:
                                if filter is not None:
                                    self._deactivate(resolved_rel)
                                res = new_relationship_token_chain
                            if cycled:
                                res = CircularRelationshipPath(res, cycled)
                            yield res
                        self._deactivate(matches)
