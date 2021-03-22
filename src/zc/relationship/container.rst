=====================
RelationshipContainer
=====================

The relationship container holds IRelationship objects. It includes an API to
search for relationships and the objects to which they link, transitively and
intransitively.  The relationships are objects in and of themselves, and they
can themselves be related as sources or targets in other relationships.

There are currently two implementations of the interface in this package.  One
uses intids, and the other uses key references.  They have different
advantages and disadvantages.

The intids makes it possible to get intid values directly.  This can make it
easier to merge the results with catalog searches and other intid-based
indexes.  Possibly more importantly, it does not create ghosted objects for
the relationships as they are searched unless absolutely necessary (for
instance, using a relationship filter), but uses the intids alone for
searches.  This can be very important if you are searching large databases of
relationships: the relationship objects and the associated keyref links in the
other implementation can flush the entire ZODB object cache, possibly leading
to unpleasant performance characteristics for your entire application.

On the other hand, there are a limited number of intids available: sys.maxint,
or 2147483647 on a 32 bit machine.  As the intid usage increases, the
efficiency of finding unique intids decreases.  This can be addressed by
increasing IOBTrees maximum integer to be 64 bit (9223372036854775807) or by
using the keyref implementation.  The keyref implementation also eliminates a
dependency--the intid utility itself--if that is desired.  This can be
important if you can't rely on having an intid utility, or if objects to be
related span intid utilities.  Finally, it's possible that the direct
attribute access that underlies the keyref implementation might be quicker
than the intid dereferencing, but this is unproven and may be false.

For our examples, we'll assume we've already imported a container and a
relationship from one of the available sources.  You can use a relationship
specific to your usage, or the generic one in shared, as long as it meets the
interface requirements.

It's also important to note that, while the relationship objects are an
important part of the design, they should not be abused.  If you want to store
other data on the relationship, it should be stored in another persistent
object, such as an attribute annotation's btree.  Typically relationship
objects will differ on the basis of interfaces, annotations, and possibly
small lightweight values on the objects themselves.

We'll assume that there is an application named `app` with 30 objects in it
(named 'ob0' through 'ob29') that we'll be relating.

Creating a relationship container is easy.  We'll use an abstract Container,
but it could be from the keyref or the intid modules.

    >>> from zc.relationship import interfaces
    >>> container = Container()
    >>> from zope.interface.verify import verifyObject
    >>> verifyObject(interfaces.IRelationshipContainer, container)
    True

The containers can be used as parts of other objects, or as standalone local
utilities.  Here's an example of adding one as a local utilty.

    >>> sm = app.getSiteManager()
    >>> sm['lineage_relationship'] = container
    >>> import zope.interface.interfaces
    >>> registry = zope.interface.interfaces.IComponentRegistry(sm)
    >>> registry.registerUtility(
    ...     container, interfaces.IRelationshipContainer, 'lineage')
    >>> import transaction
    >>> transaction.commit()

Adding relationships is also easy: instantiate and add.  The `add` method adds
objects and assigns them random alphanumeric keys.

    >>> rel = Relationship((app['ob0'],), (app['ob1'],))
    >>> verifyObject(interfaces.IRelationship, rel)
    True
    >>> container.add(rel)

Although the container does not have `__setitem__` and `__delitem__` (defining
`add` and `remove` instead), it does define the read-only elements of the basic
Python mapping interface.

    >>> container[rel.__name__] is rel
    True
    >>> len(container)
    1
    >>> list(container.keys()) == [rel.__name__]
    True
    >>> list(container) == [rel.__name__]
    True
    >>> list(container.values()) == [rel]
    True
    >>> container.get(rel.__name__) is rel
    True
    >>> container.get('17') is None
    True
    >>> rel.__name__ in container
    True
    >>> '17' in container
    False
    >>> list(container.items()) == [(rel.__name__, rel)]
    True

It also supports four searching methods: `findTargets`, `findSources`,
`findRelationships`, and `isLinked`.  Let's add a few more relationships and
examine some relatively simple cases.

    >>> container.add(Relationship((app['ob1'],), (app['ob2'],)))
    >>> container.add(Relationship((app['ob1'],), (app['ob3'],)))
    >>> container.add(Relationship((app['ob0'],), (app['ob3'],)))
    >>> container.add(Relationship((app['ob0'],), (app['ob4'],)))
    >>> container.add(Relationship((app['ob2'],), (app['ob5'],)))
    >>> transaction.commit() # this is indicative of a bug in ZODB; if you
    ... # do not do this then new objects will deactivate themselves into
    ... # nothingness when _p_deactivate is called

Now there are six direct relationships (all of the relationships point down
in the diagram)::

        ob0
        | |\
      ob1 | |
      | | | |
    ob2 ob3 ob4
      |
    ob5

The mapping methods still have kept up with the new additions.

    >>> len(container)
    6
    >>> len(container.keys())
    6
    >>> sorted(container.keys()) == sorted(
    ...     v.__name__ for v in container.values())
    True
    >>> sorted(container.items()) == sorted(
    ...     zip(container.keys(), container.values()))
    True
    >>> len([v for v in container.values() if container[v.__name__] is v])
    6
    >>> sorted(container.keys()) == sorted(container)
    True

More interestingly, lets examine some of the searching methods.  What are the
direct targets of ob0?

    >>> container.findTargets(app['ob0']) # doctest: +ELLIPSIS
    <generator object ...>

Ah-ha! It's a generator!  Let's try that again.

    >>> sorted(o.id for o in container.findTargets(app['ob0']))
    ['ob1', 'ob3', 'ob4']

OK, what about the ones no more than two relationships away?  We use the
`maxDepth` argument, which is the second placeful argument.

    >>> sorted(o.id for o in container.findTargets(app['ob0'], 2))
    ['ob1', 'ob2', 'ob3', 'ob4']

Notice that, even though ob3 is available both through one and two
relationships, it is returned only once.

Passing in None will get all related objects--the same here as passing in 3, or
any greater integer.

    >>> sorted(o.id for o in container.findTargets(app['ob0'], None))
    ['ob1', 'ob2', 'ob3', 'ob4', 'ob5']
    >>> sorted(o.id for o in container.findTargets(app['ob0'], 3))
    ['ob1', 'ob2', 'ob3', 'ob4', 'ob5']
    >>> sorted(o.id for o in container.findTargets(app['ob0'], 25))
    ['ob1', 'ob2', 'ob3', 'ob4', 'ob5']

This is true even if we put in a cycle.  We'll put in a cycle between ob5 and
ob1 and look at the results.

An important aspect of the algorithm used is that it returns closer
relationships first, which we can begin to see here.

    >>> container.add(Relationship((app['ob5'],), (app['ob1'],)))
    >>> transaction.commit()
    >>> sorted(o.id for o in container.findTargets(app['ob0'], None))
    ['ob1', 'ob2', 'ob3', 'ob4', 'ob5']
    >>> res = list(o.id for o in container.findTargets(app['ob0'], None))
    >>> sorted(res[:3]) # these are all one step away
    ['ob1', 'ob3', 'ob4']
    >>> res[3:] # ob 2 is two steps, and ob5 is three steps.
    ['ob2', 'ob5']

When you see the source in the targets, you know you are somewhere inside a
cycle.

    >>> sorted(o.id for o in container.findTargets(app['ob1'], None))
    ['ob1', 'ob2', 'ob3', 'ob5']
    >>> sorted(o.id for o in container.findTargets(app['ob2'], None))
    ['ob1', 'ob2', 'ob3', 'ob5']
    >>> sorted(o.id for o in container.findTargets(app['ob5'], None))
    ['ob1', 'ob2', 'ob3', 'ob5']

If you ask for objects of a distance that is not a positive integer, you'll get
a ValueError.

    >>> container.findTargets(app['ob0'], 0)
    Traceback (most recent call last):
    ...
    ValueError: maxDepth must be None or a positive integer
    >>> container.findTargets(app['ob0'], -1)
    Traceback (most recent call last):
    ...
    ValueError: maxDepth must be None or a positive integer
    >>> container.findTargets(app['ob0'], 'kumquat') # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: ...

The `findSources` method is the mirror of `findTargets`: given a target, it
finds all sources.  Using the same relationship tree built above, we'll search
for some sources.

    >>> container.findSources(app['ob0']) # doctest: +ELLIPSIS
    <generator object ...>
    >>> list(container.findSources(app['ob0']))
    []
    >>> list(o.id for o in container.findSources(app['ob4']))
    ['ob0']
    >>> list(o.id for o in container.findSources(app['ob4'], None))
    ['ob0']
    >>> sorted(o.id for o in container.findSources(app['ob1']))
    ['ob0', 'ob5']
    >>> sorted(o.id for o in container.findSources(app['ob1'], 2))
    ['ob0', 'ob2', 'ob5']
    >>> sorted(o.id for o in container.findSources(app['ob1'], 3))
    ['ob0', 'ob1', 'ob2', 'ob5']
    >>> sorted(o.id for o in container.findSources(app['ob1'], None))
    ['ob0', 'ob1', 'ob2', 'ob5']
    >>> sorted(o.id for o in container.findSources(app['ob3']))
    ['ob0', 'ob1']
    >>> sorted(o.id for o in container.findSources(app['ob3'], None))
    ['ob0', 'ob1', 'ob2', 'ob5']
    >>> list(o.id for o in container.findSources(app['ob5']))
    ['ob2']
    >>> list(o.id for o in container.findSources(app['ob5'], maxDepth=2))
    ['ob2', 'ob1']
    >>> sorted(o.id for o in container.findSources(app['ob5'], maxDepth=3))
    ['ob0', 'ob1', 'ob2', 'ob5']
    >>> container.findSources(app['ob0'], 0)
    Traceback (most recent call last):
    ...
    ValueError: maxDepth must be None or a positive integer
    >>> container.findSources(app['ob0'], -1)
    Traceback (most recent call last):
    ...
    ValueError: maxDepth must be None or a positive integer
    >>> container.findSources(app['ob0'], 'kumquat') # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: ...

The `findRelationships` method finds all relationships from, to, or between
two objects.  Because it supports transitive relationships, each member of the
resulting iterator is a tuple of one or more relationships.

All arguments to findRelationships are optional, but at least one of `source`
or `target` must be passed in.  A search depth defaults to one relationship
deep, like the other methods.

    >>> container.findRelationships(source=app['ob0']) # doctest: +ELLIPSIS
    <generator object ...>
    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(source=app['ob0']))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob3>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob4>,)>']]
    >>> list(container.findRelationships(target=app['ob0']))
    []
    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(target=app['ob3']))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob0>,) to (<Demo ob3>,)>'],
     ['<Relationship from (<Demo ob1>,) to (<Demo ob3>,)>']]
    >>> list(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(
    ...         source=app['ob1'], target=app['ob3']))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob1>,) to (<Demo ob3>,)>']]
    >>> container.findRelationships()
    Traceback (most recent call last):
    ...
    ValueError: at least one of `source` and `target` must be provided

They may also be used as positional arguments, with the order `source` and
`target`.

    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(app['ob1']))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob1>,) to (<Demo ob2>,)>'],
     ['<Relationship from (<Demo ob1>,) to (<Demo ob3>,)>']]
    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(app['ob5'], app['ob1']))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob5>,) to (<Demo ob1>,)>']]

`maxDepth` is again available, but it is the third positional argument now, so
keyword usage will be more frequent than with the others.  Notice that the
second path has two members: from ob1 to ob2, then from ob2 to ob5.

    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(app['ob1'], maxDepth=2))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob1>,) to (<Demo ob2>,)>'],
     ['<Relationship from (<Demo ob1>,) to (<Demo ob2>,)>',
      '<Relationship from (<Demo ob2>,) to (<Demo ob5>,)>'],
     ['<Relationship from (<Demo ob1>,) to (<Demo ob3>,)>']]

Unique relationships are returned, rather than unique objects. Therefore,
while ob3 only has two transitive sources, ob1 and ob0, it has three transitive
paths.

    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(
    ...         target=app['ob3'], maxDepth=2))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>',
      '<Relationship from (<Demo ob1>,) to (<Demo ob3>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob3>,)>'],
     ['<Relationship from (<Demo ob1>,) to (<Demo ob3>,)>'],
     ['<Relationship from (<Demo ob5>,) to (<Demo ob1>,)>',
      '<Relationship from (<Demo ob1>,) to (<Demo ob3>,)>']]

The same is true for the targets of ob0.

    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(
    ...         source=app['ob0'], maxDepth=2))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>',
      '<Relationship from (<Demo ob1>,) to (<Demo ob2>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>',
      '<Relationship from (<Demo ob1>,) to (<Demo ob3>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob3>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob4>,)>']]

Cyclic relationships are returned in a special tuple that implements
ICircularRelationshipPath.  For instance, consider all of the paths that lead
from ob0.  Notice first that all the paths are in order from shortest to
longest.

    >>> res = list(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(
    ...         app['ob0'], maxDepth=None))
    ...     # doctest: +NORMALIZE_WHITESPACE
    >>> sorted(res[:3]) # one step away # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob3>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob4>,)>']]
    >>> sorted(res[3:5]) # two steps away # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>',
      '<Relationship from (<Demo ob1>,) to (<Demo ob2>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>',
      '<Relationship from (<Demo ob1>,) to (<Demo ob3>,)>']]
    >>> res[5:] # three and four steps away # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>',
      '<Relationship from (<Demo ob1>,) to (<Demo ob2>,)>',
      '<Relationship from (<Demo ob2>,) to (<Demo ob5>,)>'],
     ['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>',
      '<Relationship from (<Demo ob1>,) to (<Demo ob2>,)>',
      '<Relationship from (<Demo ob2>,) to (<Demo ob5>,)>',
      '<Relationship from (<Demo ob5>,) to (<Demo ob1>,)>']]

The very last one is circular.

Now we'll change the expression to only include paths that implement
ICircularRelationshipPath.

    >>> list(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(
    ...         app['ob0'], maxDepth=None)
    ...         if interfaces.ICircularRelationshipPath.providedBy(path))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>',
      '<Relationship from (<Demo ob1>,) to (<Demo ob2>,)>',
      '<Relationship from (<Demo ob2>,) to (<Demo ob5>,)>',
      '<Relationship from (<Demo ob5>,) to (<Demo ob1>,)>']]

Note that, because relationships may have multiple targets, a relationship
that has a cycle may still be traversed for targets that do not generate a
cycle.  The further paths will not be marked as a cycle.

Cycle paths not only have a marker interface to identify them, but include a
`cycled` attribute that is a frozenset of the one or more searches that would
be equivalent to following the cycle(s).  If a source is provided, the searches
cycled searches would continue from the end of the path.

    >>> path = [path for path in container.findRelationships(
    ...     app['ob0'], maxDepth=None)
    ...     if interfaces.ICircularRelationshipPath.providedBy(path)][0]
    >>> path.cycled
    [{'source': <Demo ob1>}]
    >>> app['ob1'] in path[-1].targets
    True

If only a target is provided, the `cycled` search will continue from the
first relationship in the path.

    >>> path = [path for path in container.findRelationships(
    ...     target=app['ob5'], maxDepth=None)
    ...     if interfaces.ICircularRelationshipPath.providedBy(path)][0]
    >>> path # doctest: +NORMALIZE_WHITESPACE
    cycle(<Relationship from (<Demo ob5>,) to (<Demo ob1>,)>,
          <Relationship from (<Demo ob1>,) to (<Demo ob2>,)>,
          <Relationship from (<Demo ob2>,) to (<Demo ob5>,)>)
    >>> path.cycled
    [{'target': <Demo ob5>}]

maxDepth can also be used with the combination of source and target.

    >>> list(container.findRelationships(
    ...      app['ob0'], app['ob5'], maxDepth=None))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [(<Relationship from (<Demo ob0>,) to (<Demo ob1>,)>,
      <Relationship from (<Demo ob1>,) to (<Demo ob2>,)>,
      <Relationship from (<Demo ob2>,) to (<Demo ob5>,)>)]

As usual, maxDepth must be a positive integer or None.

    >>> container.findRelationships(app['ob0'], maxDepth=0)
    Traceback (most recent call last):
    ...
    ValueError: maxDepth must be None or a positive integer
    >>> container.findRelationships(app['ob0'], maxDepth=-1)
    Traceback (most recent call last):
    ...
    ValueError: maxDepth must be None or a positive integer
    >>> container.findRelationships(app['ob0'], maxDepth='kumquat')
    ... # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: ...

The `isLinked` method is a convenient way to test if two objects are linked,
or if an object is a source or target in the graph. It defaults to a maxDepth
of 1.

    >>> container.isLinked(app['ob0'], app['ob1'])
    True
    >>> container.isLinked(app['ob0'], app['ob2'])
    False

Note that maxDepth is pointless when supplying only one of source or target.

    >>> container.isLinked(source=app['ob29'])
    False
    >>> container.isLinked(target=app['ob29'])
    False
    >>> container.isLinked(source=app['ob0'])
    True
    >>> container.isLinked(target=app['ob4'])
    True
    >>> container.isLinked(source=app['ob4'])
    False
    >>> container.isLinked(target=app['ob0'])
    False

Setting maxDepth works as usual when searching for a link between two objects,
though.

    >>> container.isLinked(app['ob0'], app['ob2'], maxDepth=2)
    True
    >>> container.isLinked(app['ob0'], app['ob5'], maxDepth=2)
    False
    >>> container.isLinked(app['ob0'], app['ob5'], maxDepth=3)
    True
    >>> container.isLinked(app['ob0'], app['ob5'], maxDepth=None)
    True

As usual, maxDepth must be a positive integer or None.

    >>> container.isLinked(app['ob0'], app['ob1'], maxDepth=0)
    Traceback (most recent call last):
    ...
    ValueError: maxDepth must be None or a positive integer
    >>> container.isLinked(app['ob0'], app['ob1'], maxDepth=-1)
    Traceback (most recent call last):
    ...
    ValueError: maxDepth must be None or a positive integer
    >>> container.isLinked(app['ob0'], app['ob1'], maxDepth='kumquat')
    ... # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ValueError: ...

The `remove` method is the next to last of the core interface: it allows you
to remove relationships from a container.  It takes a relationship object.

As an example, let's remove the relationship from ob5 to ob1 that we created
to make the cycle.

    >>> res = list(container.findTargets(app['ob2'], None)) # before removal
    >>> len(res)
    4
    >>> res[:2]
    [<Demo ob5>, <Demo ob1>]
    >>> sorted(repr(o) for o in res[2:])
    ['<Demo ob2>', '<Demo ob3>']
    >>> res = list(container.findSources(app['ob2'], None)) # before removal
    >>> res[0]
    <Demo ob1>
    >>> res[3]
    <Demo ob2>
    >>> sorted(repr(o) for o in res[1:3])
    ['<Demo ob0>', '<Demo ob5>']
    >>> rel = list(container.findRelationships(app['ob5'], app['ob1']))[0][0]
    >>> rel.sources
    (<Demo ob5>,)
    >>> rel.targets
    (<Demo ob1>,)
    >>> container.remove(rel)
    >>> list(container.findRelationships(app['ob5'], app['ob1']))
    []
    >>> list(container.findTargets(app['ob2'], None)) # after removal
    [<Demo ob5>]
    >>> list(container.findSources(app['ob2'], None)) # after removal
    [<Demo ob1>, <Demo ob0>]

Finally, the `reindex` method allows objects already in the container to be
reindexed.  The default implementation of the relationship objects calls this
automatically when sources and targets are changed.

To reiterate, the relationships looked like this before. ::

        ob0
        | |\
      ob1 | |
      | | | |
    ob2 ob3 ob4
      |
    ob5

We'll switch out ob3 and ob4, so the diagram looks like this. ::

        ob0
        | |\
      ob1 | |
      | | | |
    ob2 ob4 ob3
      |
    ob5

    >>> sorted(ob.id for ob in container.findTargets(app['ob1']))
    ['ob2', 'ob3']
    >>> sorted(ob.id for ob in container.findSources(app['ob3']))
    ['ob0', 'ob1']
    >>> sorted(ob.id for ob in container.findSources(app['ob4']))
    ['ob0']
    >>> rel = next(
    ...     iter(container.findRelationships(app['ob1'], app['ob3'])
    ... ))[0]
    >>> rel.targets
    (<Demo ob3>,)

    >>> rel.targets = [app['ob4']] # this calls reindex

    >>> rel.targets
    (<Demo ob4>,)

    >>> sorted(ob.id for ob in container.findTargets(app['ob1']))
    ['ob2', 'ob4']
    >>> sorted(ob.id for ob in container.findSources(app['ob3']))
    ['ob0']
    >>> sorted(ob.id for ob in container.findSources(app['ob4']))
    ['ob0', 'ob1']

The same sort of thing happens if we change sources.  We'll change the
diagram to look like this. ::

        ob0
        | |\
      ob1 | |
      |   | |
      ob2 | ob3
      | \ |
    ob5  ob4

    >>> rel.sources
    (<Demo ob1>,)
    >>> rel.sources = (app['ob2'],) # this calls reindex
    >>> rel.sources
    (<Demo ob2>,)

    >>> sorted(ob.id for ob in container.findTargets(app['ob1']))
    ['ob2']
    >>> sorted(ob.id for ob in container.findTargets(app['ob2']))
    ['ob4', 'ob5']
    >>> sorted(ob.id for ob in container.findTargets(app['ob0']))
    ['ob1', 'ob3', 'ob4']
    >>> sorted(ob.id for ob in container.findSources(app['ob4']))
    ['ob0', 'ob2']

Advanced Usage
==============

There are four other advanced tricks that the relationship container can do:
enable search filters; allow multiple sources and targets for a single
relationship; allow relating relationships; and exposing unresolved token
results.

Search Filters
--------------

Because relationships are objects themselves, a number of interesting usages
are possible.  They can implement additional interfaces, have annotations,
and have other attributes.  One use for this is to only find objects along
relationship paths with relationships that provide a given interface.  The
`filter` argument, allowed in `findSources`, `findTargets`,
`findRelationships`, and `isLinked`, supports this kind of use case.

For instance, imagine that we change the relationships to look like the diagram
below.  The `xxx` lines indicate a relationship that implements
ISpecialRelationship. ::

        ob0
        x |x
      ob1 | x
      x   | x
      ob2 | ob3
      | x |
    ob5  ob4

That is, the relationships from ob0 to ob1, ob0 to ob3, ob1 to ob2, and ob2 to
ob4 implement the special interface.  Let's make this happen first.

    >>> from zope import interface
    >>> class ISpecialInterface(interface.Interface):
    ...     """I'm special!  So special!"""
    ...
    >>> for src, tgt in (
    ...     (app['ob0'], app['ob1']),
    ...     (app['ob0'], app['ob3']),
    ...     (app['ob1'], app['ob2']),
    ...     (app['ob2'], app['ob4'])):
    ...     rel = list(container.findRelationships(src, tgt))[0][0]
    ...     interface.directlyProvides(rel, ISpecialInterface)
    ...

Now we can use `ISpecialInterface.providedBy` as a filter for all of the
methods mentioned above.

`findTargets`

    >>> sorted(ob.id for ob in container.findTargets(app['ob0']))
    ['ob1', 'ob3', 'ob4']
    >>> sorted(ob.id for ob in container.findTargets(
    ...     app['ob0'], filter=ISpecialInterface.providedBy))
    ['ob1', 'ob3']
    >>> sorted(ob.id for ob in container.findTargets(
    ...     app['ob0'], maxDepth=None))
    ['ob1', 'ob2', 'ob3', 'ob4', 'ob5']
    >>> sorted(ob.id for ob in container.findTargets(
    ...     app['ob0'], maxDepth=None, filter=ISpecialInterface.providedBy))
    ['ob1', 'ob2', 'ob3', 'ob4']

`findSources`

    >>> sorted(ob.id for ob in container.findSources(app['ob4']))
    ['ob0', 'ob2']
    >>> sorted(ob.id for ob in container.findSources(
    ...     app['ob4'], filter=ISpecialInterface.providedBy))
    ['ob2']
    >>> sorted(ob.id for ob in container.findSources(
    ...     app['ob4'], maxDepth=None))
    ['ob0', 'ob1', 'ob2']
    >>> sorted(ob.id for ob in container.findSources(
    ...     app['ob4'], maxDepth=None, filter=ISpecialInterface.providedBy))
    ['ob0', 'ob1', 'ob2']
    >>> sorted(ob.id for ob in container.findSources(
    ...     app['ob5'], maxDepth=None))
    ['ob0', 'ob1', 'ob2']
    >>> list(ob.id for ob in container.findSources(
    ...     app['ob5'], filter=ISpecialInterface.providedBy))
    []

`findRelationships`

    >>> len(list(container.findRelationships(
    ...     app['ob0'], app['ob4'], maxDepth=None)))
    2
    >>> len(list(container.findRelationships(
    ...     app['ob0'], app['ob4'], maxDepth=None,
    ...     filter=ISpecialInterface.providedBy)))
    1
    >>> len(list(container.findRelationships(app['ob0'])))
    3
    >>> len(list(container.findRelationships(
    ...     app['ob0'], filter=ISpecialInterface.providedBy)))
    2

`isLinked`

    >>> container.isLinked(app['ob0'], app['ob5'], maxDepth=None)
    True
    >>> container.isLinked(
    ...     app['ob0'], app['ob5'], maxDepth=None,
    ...     filter=ISpecialInterface.providedBy)
    False
    >>> container.isLinked(
    ...     app['ob0'], app['ob2'], maxDepth=None,
    ...     filter=ISpecialInterface.providedBy)
    True
    >>> container.isLinked(
    ...     app['ob0'], app['ob4'])
    True
    >>> container.isLinked(
    ...     app['ob0'], app['ob4'],
    ...     filter=ISpecialInterface.providedBy)
    False

Multiple Sources and/or Targets; Duplicate Relationships
--------------------------------------------------------

Relationships are not always between a single source and a single target.  Many
approaches to this are possible, but a simple one is to allow relationships to
have multiple sources and multiple targets.  This is an approach that the
relationship container supports.

    >>> container.add(Relationship(
    ...     (app['ob2'], app['ob4'], app['ob5'], app['ob6'], app['ob7']),
    ...     (app['ob1'], app['ob4'], app['ob8'], app['ob9'], app['ob10'])))
    >>> container.add(Relationship(
    ...     (app['ob10'], app['ob0']),
    ...     (app['ob7'], app['ob3'])))

Before we examine the results, look at those for a second.

Among the interesting items is that we have duplicated the ob2->ob4
relationship in the first example, and duplicated the ob0->ob3 relationship
in the second.  The relationship container does not limit duplicate
relationships: it simply adds and indexes them, and will include the additional
relationship path in findRelationships.

    >>> sorted(o.id for o in container.findTargets(app['ob4']))
    ['ob1', 'ob10', 'ob4', 'ob8', 'ob9']
    >>> sorted(o.id for o in container.findTargets(app['ob10']))
    ['ob3', 'ob7']
    >>> sorted(o.id for o in container.findTargets(app['ob4'], maxDepth=2))
    ['ob1', 'ob10', 'ob2', 'ob3', 'ob4', 'ob7', 'ob8', 'ob9']
    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(
    ...         app['ob2'], app['ob4']))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from
       (<Demo ob2>, <Demo ob4>, <Demo ob5>, <Demo ob6>, <Demo ob7>)
       to
       (<Demo ob1>, <Demo ob4>, <Demo ob8>, <Demo ob9>, <Demo ob10>)>'],
     ['<Relationship from (<Demo ob2>,) to (<Demo ob4>,)>']]

There's also a reflexive relationship in there, with ob4 pointing to ob4.  It's
marked as a cycle.

    >>> list(container.findRelationships(app['ob4'], app['ob4']))
    ... # doctest: +NORMALIZE_WHITESPACE
    [cycle(<Relationship from
       (<Demo ob2>, <Demo ob4>, <Demo ob5>, <Demo ob6>, <Demo ob7>)
       to
       (<Demo ob1>, <Demo ob4>, <Demo ob8>, <Demo ob9>, <Demo ob10>)>,)]
    >>> list(container.findRelationships(app['ob4'], app['ob4']))[0].cycled
    [{'source': <Demo ob4>}]

Relating Relationships and Relationship Containers
--------------------------------------------------

Relationships are objects.  We've already shown and discussed how this means
that they can implement different interfaces and be annotated.  It also means
that relationships are first-class objects that can be related themselves.
This allows relationships that keep track of who created other relationships,
and other use cases.

Even the relationship containers themselves can be nodes in a relationship
container.

    >>> container1 = app['container1'] = Container()
    >>> container2 = app['container2'] = Container()
    >>> rel = Relationship((container1,), (container2,))
    >>> container.add(rel)
    >>> container.isLinked(container1, container2)
    True

Exposing Unresolved Tokens
--------------------------

For specialized use cases, usually optimizations, sometimes it is useful to
have access to raw results from a given implementation.  For instance, if a
relationship has many members, it might make sense to have an intid-based
relationship container return the actual intids.

The containers include three methods for these sorts of use cases:
`findTargetTokens`, `findSourceTokens`, and `findRelationshipTokens`.  They
take the same arguments as their similarly-named cousins.

Convenience classes
-------------------

Three convenience classes exist for relationships with a single source and/or a
single target only.

One-To-One Relationship
~~~~~~~~~~~~~~~~~~~~~~~

A `OneToOneRelationship` relates a single source to a single target.

    >>> from zc.relationship.shared import OneToOneRelationship
    >>> rel = OneToOneRelationship(app['ob20'], app['ob21'])

    >>> verifyObject(interfaces.IOneToOneRelationship, rel)
    True

All container methods work as for the general many-to-many relationship.  We
repeat some of the tests defined in the main section above (all relationships
defined there are actually one-to-one relationships).

    >>> container.add(rel)
    >>> container.add(OneToOneRelationship(app['ob21'], app['ob22']))
    >>> container.add(OneToOneRelationship(app['ob21'], app['ob23']))
    >>> container.add(OneToOneRelationship(app['ob20'], app['ob23']))
    >>> container.add(OneToOneRelationship(app['ob20'], app['ob24']))
    >>> container.add(OneToOneRelationship(app['ob22'], app['ob25']))
    >>> rel = OneToOneRelationship(app['ob25'], app['ob21'])
    >>> container.add(rel)

`findTargets`

    >>> sorted(o.id for o in container.findTargets(app['ob20'], 2))
    ['ob21', 'ob22', 'ob23', 'ob24']

`findSources`

    >>> sorted(o.id for o in container.findSources(app['ob21'], 2))
    ['ob20', 'ob22', 'ob25']

`findRelationships`

    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(app['ob21'], maxDepth=2))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob21>,) to (<Demo ob22>,)>'],
     ['<Relationship from (<Demo ob21>,) to (<Demo ob22>,)>',
      '<Relationship from (<Demo ob22>,) to (<Demo ob25>,)>'],
     ['<Relationship from (<Demo ob21>,) to (<Demo ob23>,)>']]

    >>> sorted(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(
    ...         target=app['ob23'], maxDepth=2))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob20>,) to (<Demo ob21>,)>',
      '<Relationship from (<Demo ob21>,) to (<Demo ob23>,)>'],
     ['<Relationship from (<Demo ob20>,) to (<Demo ob23>,)>'],
     ['<Relationship from (<Demo ob21>,) to (<Demo ob23>,)>'],
     ['<Relationship from (<Demo ob25>,) to (<Demo ob21>,)>',
      '<Relationship from (<Demo ob21>,) to (<Demo ob23>,)>']]

    >>> list(container.findRelationships(
    ...      app['ob20'], app['ob25'], maxDepth=None))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [(<Relationship from (<Demo ob20>,) to (<Demo ob21>,)>,
      <Relationship from (<Demo ob21>,) to (<Demo ob22>,)>,
      <Relationship from (<Demo ob22>,) to (<Demo ob25>,)>)]

    >>> list(
    ...     [repr(rel) for rel in path]
    ...     for path in container.findRelationships(
    ...         app['ob20'], maxDepth=None)
    ...         if interfaces.ICircularRelationshipPath.providedBy(path))
    ...     # doctest: +NORMALIZE_WHITESPACE
    [['<Relationship from (<Demo ob20>,) to (<Demo ob21>,)>',
      '<Relationship from (<Demo ob21>,) to (<Demo ob22>,)>',
      '<Relationship from (<Demo ob22>,) to (<Demo ob25>,)>',
      '<Relationship from (<Demo ob25>,) to (<Demo ob21>,)>']]

`isLinked`

    >>> container.isLinked(source=app['ob20'])
    True
    >>> container.isLinked(target=app['ob24'])
    True
    >>> container.isLinked(source=app['ob24'])
    False
    >>> container.isLinked(target=app['ob20'])
    False
    >>> container.isLinked(app['ob20'], app['ob22'], maxDepth=2)
    True
    >>> container.isLinked(app['ob20'], app['ob25'], maxDepth=2)
    False

`remove`

    >>> res = list(container.findTargets(app['ob22'], None)) # before removal
    >>> res[:2]
    [<Demo ob25>, <Demo ob21>]
    >>> container.remove(rel)
    >>> list(container.findTargets(app['ob22'], None)) # after removal
    [<Demo ob25>]

`reindex`

    >>> rel = next(
    ...     iter(container.findRelationships(app['ob21'], app['ob23']))
    ... )[0]

    >>> rel.target
    <Demo ob23>
    >>> rel.target = app['ob24'] # this calls reindex
    >>> rel.target
    <Demo ob24>

    >>> rel.source
    <Demo ob21>
    >>> rel.source = app['ob22'] # this calls reindex
    >>> rel.source
    <Demo ob22>

ManyToOneRelationship
~~~~~~~~~~~~~~~~~~~~~

A `ManyToOneRelationship` relates multiple sources to a single target.

    >>> from zc.relationship.shared import ManyToOneRelationship
    >>> rel = ManyToOneRelationship((app['ob22'], app['ob26']), app['ob24'])

    >>> verifyObject(interfaces.IManyToOneRelationship, rel)
    True

    >>> container.add(rel)
    >>> container.add(ManyToOneRelationship(
    ...     (app['ob26'], app['ob23']),
    ...     app['ob20']))

The relationship diagram now looks like this::

        ob20              (ob22, obj26)       (ob26, obj23)
        |   |\                  |                   |
      ob21  | |               obj24               obj20
      |     | |
    ob22    | ob23
      |  \  |
    ob25  ob24

We created a cycle for obj20 via obj23.

    >>> sorted(o.id for o in container.findSources(app['ob24'], None))
    ['ob20', 'ob21', 'ob22', 'ob23', 'ob26']

    >>> sorted(o.id for o in container.findSources(app['ob20'], None))
    ['ob20', 'ob23', 'ob26']

    >>> list(container.findRelationships(app['ob20'], app['ob20'], None))
    ... # doctest: +NORMALIZE_WHITESPACE
    [cycle(<Relationship from (<Demo ob20>,) to (<Demo ob23>,)>,
           <Relationship from (<Demo ob26>, <Demo ob23>) to (<Demo ob20>,)>)]
    >>> list(container.findRelationships(
    ...     app['ob20'], app['ob20'], 2))[0].cycled
    [{'source': <Demo ob20>}]

The `ManyToOneRelationship`'s `sources` attribute is mutable, while it's
`targets` attribute is immutable.

    >>> rel.sources
    (<Demo ob22>, <Demo ob26>)
    >>> rel.sources = [app['ob26'], app['ob24']]

    >>> rel.targets
    (<Demo ob24>,)
    >>> rel.targets = (app['ob22'],)
    Traceback (most recent call last):
    ...
    AttributeError: can't set attribute

But the relationship has an additional mutable `target` attribute.

    >>> rel.target
    <Demo ob24>
    >>> rel.target = app['ob22']

OneToManyRelationship
~~~~~~~~~~~~~~~~~~~~~

A `OneToManyRelationship` relates a single source to multiple targets.

    >>> from zc.relationship.shared import OneToManyRelationship
    >>> rel = OneToManyRelationship(app['ob22'], (app['ob20'], app['ob27']))

    >>> verifyObject(interfaces.IOneToManyRelationship, rel)
    True

    >>> container.add(rel)
    >>> container.add(OneToManyRelationship(
    ...     app['ob20'],
    ...     (app['ob23'], app['ob28'])))

The updated diagram looks like this::

        ob20              (ob26, obj24)       (ob26, obj23)
        |   |\                  |                   |
      ob21  | |               obj22               obj20
      |     | |                 |                   |
    ob22    | ob23        (ob20, obj27)       (ob23, obj28)
      |  \  |
    ob25  ob24

Alltogether there are now three cycles for ob22.

    >>> sorted(o.id for o in container.findTargets(app['ob22']))
    ['ob20', 'ob24', 'ob25', 'ob27']
    >>> sorted(o.id for o in container.findTargets(app['ob22'], None))
    ['ob20', 'ob21', 'ob22', 'ob23', 'ob24', 'ob25', 'ob27', 'ob28']

    >>> sorted(o.id for o in container.findTargets(app['ob20']))
    ['ob21', 'ob23', 'ob24', 'ob28']
    >>> sorted(o.id for o in container.findTargets(app['ob20'], None))
    ['ob20', 'ob21', 'ob22', 'ob23', 'ob24', 'ob25', 'ob27', 'ob28']

    >>> sorted(repr(c) for c in
    ...        container.findRelationships(app['ob22'], app['ob22'], None))
    ... # doctest: +NORMALIZE_WHITESPACE
    ['cycle(<Relationship from (<Demo ob22>,) to (<Demo ob20>, <Demo ob27>)>,
            <Relationship from (<Demo ob20>,) to (<Demo ob21>,)>,
            <Relationship from (<Demo ob21>,) to (<Demo ob22>,)>)',
     'cycle(<Relationship from (<Demo ob22>,) to (<Demo ob20>, <Demo ob27>)>,
            <Relationship from (<Demo ob20>,) to (<Demo ob24>,)>,
            <Relationship from (<Demo ob26>, <Demo ob24>) to (<Demo ob22>,)>)',
     'cycle(<Relationship from (<Demo ob22>,) to (<Demo ob24>,)>,
            <Relationship from (<Demo ob26>, <Demo ob24>) to (<Demo ob22>,)>)']

The `OneToManyRelationship`'s `targets` attribute is mutable, while it's
`sources` attribute is immutable.

    >>> rel.targets
    (<Demo ob20>, <Demo ob27>)
    >>> rel.targets = [app['ob28'], app['ob21']]

    >>> rel.sources
    (<Demo ob22>,)
    >>> rel.sources = (app['ob23'],)
    Traceback (most recent call last):
    ...
    AttributeError: can't set attribute

But the relationship has an additional mutable `source` attribute.

    >>> rel.source
    <Demo ob22>
    >>> rel.target = app['ob23']
