The Relationship package currently contains two main types of components: a
relationship index, and some relationship containers.  Both are designed for
use within the ZODB.  They share the model that relationships are full-fledged
objects that are indexed for optimized searches.  They also share the ability
to perform optimized intransitive and transitive relationship searches, and
have, or can be configured to have, arbitrary filter searches on relationship
objects.

The index is a very generic component that can be used to optimize searches
for N-ary relationships, can be used standalone or within a catalog, can be
used with pluggable token generation schemes, and generally tries to provide
a relatively policy-free tool.  It is expected to be used primarily as an
engine for more specialized and constrained tools and APIs.

The relationship containers use the index to manage two-way relationships,
either using a container interface or a listcontainer interface.  They are a
good example of the index in standalone use.

This document describes the relationship index.  See container.txt for
documentation of the relationship container, and listcontainer.txt for
documentation of the relationship list container.

=====
Index
=====

The index interface searches for object and relationship tokens.  Let's look
at some examples of the core capabilities.

To use a relationship index, you need to have interface attributes, or methods
callable with no arguments, that are treated as relationship pointers.  The
pointers may be a collection of items or a single item.

To exercise the index, we'll come up with a somewhat complex relationship to
index. Let's say we are modeling a generic set-up like SUBJECT
RELATIONSHIPTYPE OBJECT in CONTEXT.  This could let you let users define
relationship types, then index them on the fly.  The context can be something
like a project, so we could say

[Fred (SUBJECT)] [has the role of (RELATIONSHIPTYPE)]
[Project Manager (OBJECT)] on the [zope.org redesign project (CONTEXT)].

So let's define a basic interface without the context, and then an extended
interface with the context.

    >>> from zope import interface
    >>> class IRelationship(interface.Interface):
    ...     subjects = interface.Attribute(
    ...         'The sources of the relationship; the subject of the sentence')
    ...     relationshiptype = interface.Attribute(
    ...         '''the single relationship type of this relationship;
    ...         usually contains the verb of the sentence.''')
    ...     objects = interface.Attribute(
    ...         '''the targets of the relationship; usually a direct or
    ...         indirect object in the sentence''')
    ...
    >>> class IContextAwareRelationship(IRelationship):
    ...     def getContext():
    ...         '''return a context for the relationship'''
    ...

Now we'll create an index.  To do that, we must minimally pass in a callable
that, given an object, the index, and a cache to optimize lookups in, will
return an integer token for the object.  You can use non-integer values (see
the keyref reference container, for instance) but you must pass in additional
values.  The index also expects relationship tokens to be integers by default--
this can also be customized (again see the keyref reference container).

For now, we will have a very simple token generator and resolver.  Often this
will involve utilities like the intid utility (see the intid reference
container).

    >>> import random
    >>> def makeTokenTools(checkArgs=True):
    ...     lookup = {}
    ...     def generateToken(obj, index=None, cache=None):
    ...         if checkArgs:
    ...             assert index is not None and cache is not None, (
    ...                 'did not receive correct arguments')
    ...         token = getattr(obj, '_z_token__', None)
    ...         if token is None:
    ...             token = random.randrange(-2147483648, 2147483647)
    ...             while token in lookup:
    ...                 token = random.randrange(-2147483648, 2147483647)
    ...             obj._z_token__ = token
    ...             lookup[token] = obj
    ...         return token
    ...     def resolveToken(token):
    ...         return lookup[token]
    ...     return lookup, generateToken, resolveToken
    ...
    >>> objDict, objGenerateToken, objResolveToken = makeTokenTools()
    >>> relDict, relGenerateToken, relResolveToken = makeTokenTools(False)

Now we can make an index.  We are going to disable the _p_deactivate
optimization, since we are not really using this within the ZODB.

We are going to use the simple transitive query factory defined in the index
module for our default transitive behavior: when you want to do transitive
searches, transpose 'subjects' with 'targets' and keep everything else.  If
both subjects and targets are provided, don't do any transitive search (by
default).

    >>> from zc.relationship import index
    >>> from zc.relationship import interfaces
    >>> from zope.interface.verify import verifyObject
    >>> factory = index.TransposingTransitiveQueriesFactory(
    ...     'subjects', 'objects')
    >>> verifyObject(interfaces.ITransitiveQueriesFactory, factory)
    True
    >>> ix = index.Index(
    ...     ({'element': IRelationship['subjects']},
    ...      {'element': IRelationship['relationshiptype'], 
    ...                  'single': True},
    ...      {'element': IRelationship['objects']},
    ...      {'element': IContextAwareRelationship['getContext'], 
    ...                  'single': True}),
    ...     objGenerateToken, factory, deactivateSets=False)
    >>> verifyObject(interfaces.IIndex, ix)
    True

Now we'll create some representative objects that we can relate, and create
the example relationship we described above.  The context will only be
available as an adapter to ISpecialRelationship objects.

    >>> class Base(object):
    ...     def __init__(self, name):
    ...         self.name = name
    ...     def __repr__(self):
    ...         return '<%s %r>' % (self.__class__.__name__, self.name)
    ...
    >>> class Person(Base): pass
    ...
    >>> class RelationshipType(Base): pass
    ...
    >>> class Role(Base): pass
    ...
    >>> class Project(Base): pass
    ...
    >>> class Company(Base): pass
    ...
    >>> class Relationship(object):
    ...     interface.implements(IRelationship)
    ...     def __init__(self, subjects, relationshiptype, objects):
    ...         self.subjects = subjects
    ...         self.relationshiptype = relationshiptype
    ...         self.objects = objects
    ...     def __repr__(self):
    ...         return '<%r %r %r>' % (
    ...             self.subjects, self.relationshiptype, self.objects)
    ...
    >>> class ISpecialRelationship(interface.Interface):
    ...     pass
    ...
    >>> from zope import component
    >>> class ContextRelationshipAdapter(object):
    ...     component.adapts(ISpecialRelationship)
    ...     interface.implements(IContextAwareRelationship)
    ...     def __init__(self, adapted):
    ...         self.adapted = adapted
    ...     def getContext(self):
    ...         return getattr(self.adapted, '_z_context__', None)
    ...     def setContext(self, value):
    ...         self.adapted._z_context__ = value
    ...     def __getattr__(self, name):
    ...         return getattr(self.adapted, name)
    ...
    >>> component.provideAdapter(ContextRelationshipAdapter)
    >>> class SpecialRelationship(Relationship):
    ...     interface.implements(ISpecialRelationship)
    ...
    >>> people = {}
    >>> for p in ['Abe', 'Bran', 'Cathy', 'David', 'Emily', 'Fred', 'Gary',
    ...           'Heather', 'Ingrid', 'Jim', 'Karyn', 'Lee', 'Mary',
    ...           'Nancy', 'Olaf', 'Perry', 'Quince', 'Rob', 'Sam', 'Terry',
    ...           'Uther', 'Van', 'Warren', 'Xen', 'Ygritte', 'Zane']:
    ...     people[p] = Person(p)
    ...
    >>> rels = {}
    >>> for r in ['has the role of', 'manages', 'taught', 'commissioned']:
    ...     rels[r] = RelationshipType(r)
    ...
    >>> roles = {}
    >>> for r in ['Project Manager', 'Software Engineer', 'Designer',
    ...           'Systems Administrator', 'Team Leader', 'Mascot']:
    ...     roles[r] = Role(r)
    ...
    >>> projects = {}
    >>> for p in ['zope.org redesign', 'Zope 3 manual',
    ...           'improved test coverage', 'Vault design and implementation']:
    ...     projects[p] = Project(p)
    ...
    >>> companies = {}
    >>> for c in ['Ynod Corporation', 'HAL, Inc.', 'Zookd']:
    ...     companies[c] = Company(c)
    ...
    >>> rel = SpecialRelationship(
    ...     (people['Fred'],),
    ...     rels['has the role of'],
    ...     (roles['Project Manager'],))
    >>> IContextAwareRelationship(rel).setContext(
    ...     projects['zope.org redesign'])
    >>> ix.index_doc(relGenerateToken(rel), rel)

Basic searching
===============

Now that we have indexed the first example relationship, we can search for it.
The base index interface defines five searching methods: `isLinked`,
`findRelationshipChains`, `findRelationships`, `findValues`, and
the standard zope.index method `apply`.  The `apply` method essentially
exposes the `findRelationships` and `findValues` methods via a query
object spelling.

Here, we ask 'who has the role of project manager in the zope.org redesign?'.
Notice that all queries must use tokens, not actual objects; however, the index
provides a method to ease that requirement, in the form of a `tokenizeQuery`
method that converts a dict with objects to a dict with tokens.  We shorten the
call by stashing it away.

    >>> q = ix.tokenizeQuery
    >>> [objResolveToken(t) for t in ix.findValues(
    ...     'subjects',
    ...     q({'relationshiptype': rels['has the role of'],
    ...       'objects': roles['Project Manager'],
    ...       'getContext': projects['zope.org redesign']}))]
    [<Person 'Fred'>]

If we want to find all the relationships for which Fred is a subject, we can
use `findRelationships`.

    >>> [relResolveToken(t) for t in ix.findRelationships(
    ...     q({'subjects': people['Fred']}))] # doctest: +NORMALIZE_WHITESPACE
    [<(<Person 'Fred'>,) <RelationshipType 'has the role of'>
      (<Role 'Project Manager'>,)>]

The apply method, part of the zope.index.interfaces.IIndexSearch interface,
can essentially only duplicate those two search calls.  The only additional
functionality is that the results always are IFBTree sets.  A wrapper dict
specifies the type of search with the key, and the value should be the
arguments for the search.

Here, we ask for the current known roles on the zope.org redesign.

    >>> res = ix.apply({'values':
    ...     {'resultName': 'objects', 'query':
    ...         q({'relationshiptype': rels['has the role of'],
    ...            'getContext': projects['zope.org redesign']})}})
    >>> res # doctest: +ELLIPSIS
    IFSet([...])
    >>> [objResolveToken(t) for t in res]
    [<Role 'Project Manager'>]

Here, we ask for the relationships that have the 'has the role of' type.

    >>> res = ix.apply({'relationships':
    ...     q({'relationshiptype': rels['has the role of']})})
    >>> res # doctest: +ELLIPSIS
    <BTrees._IFBTree.IFTreeSet object at ...>
    >>> [relResolveToken(t) for t in res]
    ... # doctest: +NORMALIZE_WHITESPACE
    [<(<Person 'Fred'>,) <RelationshipType 'has the role of'>
      (<Role 'Project Manager'>,)>]

The last two basic search methods, `isLinked` and
`findRelationshipChains`, are most useful for transitive searches.  We
have not yet created any relationships that we can use transitively.  They
still will work with intransitive searches, so we will demonstrate them here
as an introduction.

`findRelationshipChains` lets you find transitive relationship paths.
Right now a single relationship--a single point--can't create much of a line.
So first, here's a useless example:

    >>> [[relResolveToken(t) for t in path] for path in
    ...  ix.findRelationshipChains(
    ...     q({'relationshiptype': rels['has the role of']}))]
    ... # doctest: +NORMALIZE_WHITESPACE
    [[<(<Person 'Fred'>,) <RelationshipType 'has the role of'>
      (<Role 'Project Manager'>,)>]]

That's useless, because there's no chance of it being a transitive search, and
so you might as well use findRelationships.  This will become more
interesting later on.

`isLinked` returns a boolean if there is at least one path that matches the
search--in fact, the implementation is essentially

    try:
        iter(ix.findRelationshipChains(...args...)).next()
    except StopIteration:
        return False
    else:
        return True

So, we can say

    >>> ix.isLinked(q({'subjects': people['Fred']}))
    True
    >>> ix.isLinked(q({'subjects': people['Gary']}))
    False
    >>> ix.isLinked(q({'subjects': people['Fred'],
    ...                'relationshiptype': rels['manages']}))
    False

This is reasonably useful as is, to test basic assertions.  It also works with
transitive searches, as we will see below.

Searching for empty sets
------------------------

We've examined the most basic search capabilities.  One other feature of the
index and search is that one can search for relationships to an empty set, or,
for single-value relationships like 'relationshiptype' and 'getContext' in our
examples, None.

Let's add a relationship with a 'manages' relationshiptype, and no context; and
a relationship with a 'commissioned' relationship type, and a company context.

    >>> rel = Relationship(
    ...     (people['Abe'],), rels['manages'], (people['Bran'],))
    >>> ix.index_doc(relGenerateToken(rel), rel)
    >>> rel = SpecialRelationship(
    ...     (people['Abe'],), rels['commissioned'],
    ...     (projects['Vault design and implementation'],))
    >>> IContextAwareRelationship(rel).setContext(companies['Zookd'])
    >>> ix.index_doc(relGenerateToken(rel), rel)

Now we can search for Abe's relationship that does not have a context.  The
None value is always used to match both an empty set and a single `None` value.
The index does not support any other "empty" values at this time.

    >>> sorted(
    ...     repr(objResolveToken(t)) for t in ix.findValues(
    ...         'objects',
    ...         q({'subjects': people['Abe']})))
    ["<Person 'Bran'>", "<Project 'Vault design and implementation'>"]
    >>> [objResolveToken(t) for t in ix.findValues(
    ...     'objects',
    ...     q({'subjects': people['Abe'], 'getContext': None}))]
    [<Person 'Bran'>]

Note that the index does not currently support searching for relationships that
have any value, or one of a set of values.

Working with transitive searches
================================

It's possible to do transitive searches as well.  This can let you find all
transitive bosses, or transitive subordinates, in our 'manages' relationship
type.  Let's set up some example relationships.  Using letters to represent our
people, we'll create three heirarchies like this:

        A        JK           R
       / \      /  \           
      B   C    LM   NOP     S T U
     / \  |     |          /| |  \
    D  E  F     Q         V W X   |
    |     |                    \--Y
    H     G                       |
    |                             Z
    I

We already have a relationship from Abe to Bran, so we'll only be adding the
rest.

    >>> relmap = (
    ...     ('A', 'C'), ('B', 'D'), ('B', 'E'), ('C', 'F'),
    ...     ('F', 'G'), ('D', 'H'), ('H', 'I'), ('JK', 'LM'), ('JK', 'NOP'),
    ...     ('LM', 'Q'), ('R', 'STU'), ('S', 'VW'), ('T', 'X'), ('UX', 'Y'),
    ...     ('Y', 'Z'))
    >>> letters = dict((name[0], ob) for name, ob in people.items())
    >>> for subs, obs in relmap:
    ...     subs = tuple(letters[l] for l in subs)
    ...     obs = tuple(letters[l] for l in obs)
    ...     rel = Relationship(subs, rels['manages'], obs)
    ...     ix.index_doc(relGenerateToken(rel), rel)
    ...

Now we can do both transitive and intransitive searches.  Here are a few
examples.

    >>> [objResolveToken(t) for t in ix.findValues(
    ...     'subjects',
    ...     q({'objects': people['Ingrid'],
    ...        'relationshiptype': rels['manages']}))
    ...     ]
    [<Person 'Heather'>, <Person 'David'>, <Person 'Bran'>, <Person 'Abe'>]

Notice that they are in order, walking away from the search start.  It also
is breadth-first--for instance, look at the list of superiors to Zane: Xen and
Uther come before Rob and Terry.

    >>> res = [objResolveToken(t) for t in ix.findValues(
    ...     'subjects',
    ...     q({'objects': people['Zane'], 'relationshiptype': rels['manages']})
    ...     )]
    >>> res[0]
    <Person 'Ygritte'>
    >>> sorted(repr(p) for p in res[1:3])
    ["<Person 'Uther'>", "<Person 'Xen'>"]
    >>> sorted(repr(p) for p in res[3:])
    ["<Person 'Rob'>", "<Person 'Terry'>"]

Notice that all the elements of the search are maintained as it is walked--only
the transposed values are changed, and the rest remain statically.  For
instance, notice the difference between these two results.

    >>> [objResolveToken(t) for t in ix.findValues(
    ...     'objects',
    ...     q({'subjects': people['Cathy'],
    ...        'relationshiptype': rels['manages']}))]
    [<Person 'Fred'>, <Person 'Gary'>]
    >>> res = [objResolveToken(t) for t in ix.findValues(
    ...     'objects',
    ...     q({'subjects': people['Cathy']}))]
    >>> res[0]
    <Person 'Fred'>
    >>> sorted(repr(i) for i in res[1:])
    ["<Person 'Gary'>", "<Role 'Project Manager'>"]

The first search got what we expected for our management relationshiptype--
walking from Cathy, the relationshiptype was maintained, and we only got the
Gary subordinate.  The second search didn't specify the relationshiptype, so
the transitive search included the Role we added first (Fred has the role of
Project Manager for the zope.org redesign).

The `maxDepth` argument allows control over how far to search.  For instance,
if we only want to search for Bran's subordinates a maximum of two steps deep,
we can do so:

    >>> res = [objResolveToken(t) for t in ix.findValues(
    ...     'objects',
    ...     q({'subjects': people['Bran']}),
    ...     maxDepth=2)]
    >>> sorted(repr(i) for i in res)
    ["<Person 'David'>", "<Person 'Emily'>", "<Person 'Heather'>"]

A minimum depth--a number of relationships that must be traversed before
results are desired--can also be achieved trivially using the targetFilter
argument described soon below.  For now, we will continue in the order of the
arguments list, so `filter` is up next.

The `filter` argument takes an object (such as a function) that provides
interfaces.IFilter.  As the interface lists, it receives the current chain
of relationship tokens ("relchain"), the original query that started the search
("query"), the index object ("index"), and a dictionary that will be used
throughout the search and then discarded that can be used for optimizations
("cache").  It should return a boolean, which determines whether the given
relchain should be used at all--traversed or returned.  For instance, if
security dictates that the current user can only see certain relationships,
the filter could be used to make only the available relationships traversable.
Other uses are only getting relationships that were created after a given time,
or that have some annotation (available after resolving the token).

Let's look at an example of a filter that only allows relationships in a given
set, the way a security-based filter might work.  We'll then use it to model
a situation in which the current user can't see that Ygritte is managed by
Uther, in addition to Xen.

    >>> s = set(relDict)
    >>> relset = list(ix.findRelationships(q({'subjects': people['Xen']})))
    >>> len(relset)
    1
    >>> s.remove(relset[0])
    >>> objGenerateToken(people['Uther'], 1, 1) in list(
    ...     ix.findValues('subjects', q({'objects': people['Ygritte']})))
    True
    >>> objGenerateToken(people['Uther'], 1, 1) in list(ix.findValues(
    ...     'subjects', q({'objects': people['Ygritte']}),
    ...     filter=lambda relchain, query, index, cache: relchain[-1] in s))
    False

The next two search arguments are the targetQuery and the targetFilter.  They
both are filters on the output of the search methods, while not affecting the
traversal/search process.  The targetQuery takes a query identical to the main
query, and the targetFilter takes an IFilter identical to the one used by the
`filter` argument.  The targetFilter can do all of the work of the targetQuery,
but the targetQuery makes a common case--wanting to find the paths between two
objects, or if two objects are linked at all, for instance--convenient.

We'll skip over targetQuery for a moment (we'll return when we revisit
`findRelationshipChains` and `isLinked`), and look at targetFilter.  
targetFilter can be used for many tasks, such as only returning values that
are in specially annotated relationships, or only returning values that have
traversed a certain hinge relationship in a two-part search, or other tasks.
A very simply one, though, is to effectively specify a minimum traversal depth.
Here, we find the people who are precisely two steps down from Bran, no more
and no less.

    >>> res = [objResolveToken(t) for t in ix.findValues(
    ...     'objects',
    ...     q({'subjects': people['Bran']}),
    ...     maxDepth=2,
    ...     targetFilter=lambda relchain, q, i, c: len(relchain)>=2)]
    >>> sorted(repr(i) for i in res)
    ["<Person 'Heather'>"]

Heather is the only person precisely two steps down from Bran.

Notice that we specified both maxDepth and targetFilter.  We could have
received the same output by specifying a targetFilter of `len(relchain)==2`
and no maxDepth, but there is an important difference in efficiency.  maxDepth
and filter can reduce the amount of work done by the index because they can
stop searching after reaching the maxDepth, or failing the filter; the 
targetFilter and targetQuery arguments simply hide the results obtained, which
can reduce a bit of work in the case of getValues but generally don't reduce
any of the traversal work.

The last argument to the search methods is `transitiveQueriesFactory`.  It is
a powertool that replaces the index's default traversal factory for the
duration of the search.  This allows custom traversal for individual searches,
and can support a number of advanced use cases.  For instance, our index
assumes that you want to traverse objects and sources, and that the context
should be constant; that may not always be the desired traversal behavior.  If
we had a relationship of PERSON1 TAUGHT PERSON2 (the lessons of PERSON3) then
to find the teachers of any given person you might want to traverse PERSON1,
but sometimes you might want to traverse PERSON3 as well.  You can change the
behavior by providing a different factory.

To show this example we will need to add a few more relationships.  We will say
that Mary teaches Rob the lessons of Abe; Olaf teaches Zane the lessons of
Bran; Cathy teaches Bran the lessons of Lee; David teaches Abe the lessons of
Zane; and Emily teaches Mary the lessons of Ygritte.

In the diagram, left-hand lines indicate "taught" and right-hand lines indicate
"the lessons of", so 

  E   Y
   \ /
    M

should be read as "Emily taught Mary the lessons of Ygritte".

            C   L
             \ /
          O   B
           \ /
  E   Y D   Z
   \ /   \ /
    M     A
     \   /
      \ /
       R

You can see then that the transitive path of Rob's teachers is Mary and Emily,
but the transitive path of Rob's lessons is Abe, Zane, Bran, and Lee.

    >>> for triple in ('EMY', 'MRA', 'DAZ', 'OZB', 'CBL'):
    ...     teacher, student, source = (letters[l] for l in triple)
    ...     rel = SpecialRelationship((teacher,), rels['taught'], (student,))
    ...     IContextAwareRelationship(rel).setContext(source)
    ...     ix.index_doc(relGenerateToken(rel), rel)
    ...
    >>> [objResolveToken(t) for t in ix.findValues(
    ...     'subjects',
    ...     q({'objects': people['Rob'], 'relationshiptype': rels['taught']}))]
    [<Person 'Mary'>, <Person 'Emily'>]
    >>> [objResolveToken(t) for t in ix.findValues(
    ...     'getContext',
    ...     q({'objects': people['Rob'], 'relationshiptype': rels['taught']}),
    ...     transitiveQueriesFactory=index.TransposingTransitiveQueriesFactory(
    ...         'objects', 'getContext'))]
    [<Person 'Abe'>, <Person 'Zane'>, <Person 'Bran'>, <Person 'Lee'>]

transitiveQueryFactories can be very powerful, and we aren't finished talking
about them in this document: see "Transitively mapping multiple elements"
below.

We have now discussed, or at least mentioned, all of the available search
arguments.  The `apply` method's 'values' search has the same arguments and
features as `findValues`, so it can also do these transitive tricks.  Let's
get all of Karyn's subordinates.

    >>> res = ix.apply({'values':
    ...     {'resultName': 'objects', 'query':
    ...         q({'relationshiptype': rels['manages'],
    ...           'subjects': people['Karyn']})}})
    >>> res # doctest: +ELLIPSIS
    IFSet([...])
    >>> sorted(repr(objResolveToken(t)) for t in res)
    ... # doctest: +NORMALIZE_WHITESPACE
    ["<Person 'Lee'>", "<Person 'Mary'>", "<Person 'Nancy'>",
     "<Person 'Olaf'>", "<Person 'Perry'>", "<Person 'Quince'>"]

As we return to `findRelationshipChains`, we also return to the search
argument we postponed above: targetQuery.  

The `findRelationshipChains` can simply find all paths:

    >>> res = [repr([relResolveToken(t) for t in path]) for path in
    ...  ix.findRelationshipChains(
    ...     q({'relationshiptype': rels['manages'], 'subjects': people['Jim']}
    ...     ))]
    >>> len(res)
    3
    >>> sorted(res[:2]) # doctest: +NORMALIZE_WHITESPACE
    ["[<(<Person 'Jim'>, <Person 'Karyn'>) <RelationshipType 'manages'>
        (<Person 'Lee'>, <Person 'Mary'>)>]",
     "[<(<Person 'Jim'>, <Person 'Karyn'>) <RelationshipType 'manages'>
        (<Person 'Nancy'>, <Person 'Olaf'>, <Person 'Perry'>)>]"]
    >>> res[2] # doctest: +NORMALIZE_WHITESPACE
    "[<(<Person 'Jim'>, <Person 'Karyn'>) <RelationshipType 'manages'>
       (<Person 'Lee'>, <Person 'Mary'>)>,
      <(<Person 'Lee'>, <Person 'Mary'>) <RelationshipType 'manages'>
       (<Person 'Quince'>,)>]"

Like `findValues`, this is a breadth-first search.

If we use a targetQuery with `findRelationshipChains`, you can find all paths
between two searches. For instance, consider the paths between Rob and
Ygritte.  While a `findValues` search would only include Rob once if asked to
search for supervisors, there are two paths.  These can be found with the
targetSearch.

    >>> res = [repr([relResolveToken(t) for t in path]) for path in
    ...  ix.findRelationshipChains(
    ...     q({'relationshiptype': rels['manages'],
    ...        'subjects': people['Rob']}),
    ...     targetQuery=q({'objects': people['Ygritte']}))]
    >>> len(res)
    2
    >>> sorted(res[:2]) # doctest: +NORMALIZE_WHITESPACE
    ["[<(<Person 'Rob'>,) <RelationshipType 'manages'>
        (<Person 'Sam'>, <Person 'Terry'>, <Person 'Uther'>)>,
       <(<Person 'Terry'>,) <RelationshipType 'manages'> (<Person 'Xen'>,)>,
       <(<Person 'Uther'>, <Person 'Xen'>) <RelationshipType 'manages'>
        (<Person 'Ygritte'>,)>]",
     "[<(<Person 'Rob'>,) <RelationshipType 'manages'>
        (<Person 'Sam'>, <Person 'Terry'>, <Person 'Uther'>)>,
       <(<Person 'Uther'>, <Person 'Xen'>) <RelationshipType 'manages'>
        (<Person 'Ygritte'>,)>]"] 

`isLinked` takes the same arguments as all of the other transitive-aware
methods.  For instance, Rob and Ygritte are transitively linked, but Abe and
Zane are not.

    >>> ix.isLinked(
    ...     q({'relationshiptype': rels['manages'],
    ...        'subjects': people['Rob']}),
    ...     targetQuery=q({'objects': people['Ygritte']}))
    True
    >>> ix.isLinked(
    ...     q({'relationshiptype': rels['manages'],
    ...        'subjects': people['Abe']}),
    ...     targetQuery=q({'objects': people['Ygritte']}))
    False

Detecting cycles
----------------

Suppose we're modeling a 'king in disguise': someone high up in management also
works as a peon to see how his employees' lives are.  We could model this a
number of ways that might make more sense than what we'll do now, but to show
cycles at work we'll just add an additional relationship so that Abe works for
Gary.  That means that the very longest path from Ingrid up gets a lot longer--
in theory, it's infinitely long, because of the cycle.

The index keeps track of this and stops right when the cycle happens, and right
before the cycle duplicates any relationships.  It marks the chain that has
cycle as a special kind of tuple that implements ICircularRelationshipPath.
the tuple has a 'cycled' attribute that contains the one or more searches
that would be equivalent to following the cycle (given the same transitiveMap).

Let's actually look at the example we described.

    >>> res = list(ix.findRelationshipChains(
    ...     q({'objects': people['Ingrid'],
    ...        'relationshiptype': rels['manages']})))
    >>> len(res)
    4
    >>> len(res[3])
    4
    >>> interfaces.ICircularRelationshipPath.providedBy(res[3])
    False
    >>> rel = Relationship(
    ...     (people['Gary'],), rels['manages'], (people['Abe'],))
    >>> ix.index_doc(relGenerateToken(rel), rel)
    >>> res = list(ix.findRelationshipChains(
    ...     q({'objects': people['Ingrid'],
    ...        'relationshiptype': rels['manages']})))
    >>> len(res)
    8
    >>> len(res[7])
    8
    >>> interfaces.ICircularRelationshipPath.providedBy(res[7])
    True
    >>> [sorted(
    ...     (nm, objResolveToken(t))
    ...     for nm, t in search.items()) for search in res[7].cycled]
    ... # doctest: +NORMALIZE_WHITESPACE
    [[('objects', <Person 'Abe'>),
      ('relationshiptype', <RelationshipType 'manages'>)]]

Notice that there is nothing special about the new relationship, by the way.
If we had started to look for Fred's supervisors, the cycle marker would have
been given for the relationship that points back to Fred as a supervisor to
himself.  There's no way for the computer to know which is the "cause" without
further help and policy.

Handling cycles can be tricky.  Now imagine that we have a cycle that involves
a relationship with two objects, only one of which causes the cycle.  The other
object should continue to be followed.

For instance, lets have Q manage L and Y.  The link to L will be a cycle, but
the link to Y is not, and should be followed.  This means that only the middle
relationship chain will be marked as a cycle.

    >>> rel = Relationship((people['Quince'],), rels['manages'],
    ...                    (people['Lee'], people['Ygritte']))
    >>> ix.index_doc(relGenerateToken(rel), rel)
    >>> res = [p for p in ix.findRelationshipChains(
    ...     q({'relationshiptype': rels['manages'],
    ...        'subjects': people['Mary']}))]
    >>> [interfaces.ICircularRelationshipPath.providedBy(p) for p in res]
    [False, True, False]
    >>> [[relResolveToken(t) for t in p] for p in res]
    ... # doctest: +NORMALIZE_WHITESPACE
    [[<(<Person 'Lee'>, <Person 'Mary'>) <RelationshipType 'manages'>
       (<Person 'Quince'>,)>],
     [<(<Person 'Lee'>, <Person 'Mary'>) <RelationshipType 'manages'>
       (<Person 'Quince'>,)>,
      <(<Person 'Quince'>,) <RelationshipType 'manages'>
       (<Person 'Lee'>, <Person 'Ygritte'>)>],
     [<(<Person 'Lee'>, <Person 'Mary'>) <RelationshipType 'manages'>
       (<Person 'Quince'>,)>,
      <(<Person 'Quince'>,) <RelationshipType 'manages'>
       (<Person 'Lee'>, <Person 'Ygritte'>)>,
      <(<Person 'Ygritte'>,) <RelationshipType 'manages'> (<Person 'Zane'>,)>]]
    >>> [sorted(
    ...     (nm, objResolveToken(t))
    ...     for nm, t in search.items()) for search in res[1].cycled]
    ... # doctest: +NORMALIZE_WHITESPACE
    [[('relationshiptype', <RelationshipType 'manages'>),
      ('subjects', <Person 'Lee'>)]]

Transitively mapping multiple elements
--------------------------------------

Transitive searches can do whatever searches the transitiveQueriesFactory 
returns, which means that complex transitive behavior can be modeled.  For
instance, imagine genealogical relationships.  Let's say the basic
relationship is "MALE and FEMALE had CHILDREN".  Walking transitively to get
ancestors or descendents would need to distinguish between male children and
female children in order to correctly generate the transitive search.  This
could be accomplished by resolving each child token and examining the object
or, probably more efficiently, getting an indexed collection of males and
females (and cacheing it in the cache dictionary for further transitive steps)
and checking the gender by membership in the indexed collections.  Either of
these approaches could be performed by a transitiveQueriesFactory.  A full
example is left as an exercise to the reader.

Lies, damn lies, and statistics
===============================

The zope.index.interfaces.IStatistics methods are implemented to provide
minimal introspectability.  wordCount always returns 0, because words are
irrelevant to this kind of index.  documentCount returns the number of
relationships indexed.

    >>> ix.wordCount()
    0
    >>> ix.documentCount()
    25

Reindexing and removing relationships
=====================================

Using an index over an application's lifecycle usually requires changes to the
indexed objects.  As per the zope.index interfaces, `index_doc` can reindex
relationships, `unindex_doc` can remove them, and `clear` can clear the entire
index.

Here we change the zope.org project manager from Fred to Emily.

    >>> [objResolveToken(t) for t in ix.findValues(
    ...     'subjects',
    ...     q({'relationshiptype': rels['has the role of'],
    ...       'objects': roles['Project Manager'],
    ...       'getContext': projects['zope.org redesign']}))]
    [<Person 'Fred'>]
    >>> rel = relResolveToken(list(ix.findRelationships(
    ...     q({'relationshiptype': rels['has the role of'],
    ...       'objects': roles['Project Manager'],
    ...       'getContext': projects['zope.org redesign']})))[0])
    >>> rel.subjects = (people['Emily'],)
    >>> ix.index_doc(relGenerateToken(rel), rel)
    >>> q = ix.tokenizeQuery
    >>> [objResolveToken(t) for t in ix.findValues(
    ...     'subjects',
    ...     q({'relationshiptype': rels['has the role of'],
    ...       'objects': roles['Project Manager'],
    ...       'getContext': projects['zope.org redesign']}))]
    [<Person 'Emily'>]

Here we remove the relationship that made a cycle for Abe in the 'king in
disguise' scenario.

    >>> res = list(ix.findRelationshipChains(
    ...     q({'objects': people['Ingrid'],
    ...        'relationshiptype': rels['manages']})))
    >>> len(res)
    8
    >>> len(res[7])
    8
    >>> interfaces.ICircularRelationshipPath.providedBy(res[7])
    True
    >>> rel = relResolveToken(list(ix.findRelationships(
    ...     q({'subjects': people['Gary'], 'relationshiptype': rels['manages'],
    ...        'objects': people['Abe']})))[0])
    >>> ix.unindex_doc(relGenerateToken(rel))
    >>> ix.documentCount()
    24
    >>> res = list(ix.findRelationshipChains(
    ...     q({'objects': people['Ingrid'],
    ...        'relationshiptype': rels['manages']})))
    >>> len(res)
    4
    >>> len(res[3])
    4
    >>> interfaces.ICircularRelationshipPath.providedBy(res[3])
    False

Finally we clear out the whole index.

    >>> ix.clear()
    >>> ix.documentCount()
    0
    >>> list(ix.findRelationshipChains(
    ...     q({'objects': people['Ingrid'],
    ...        'relationshiptype': rels['manages']})))
    []
    >>> [objResolveToken(t) for t in ix.findValues(
    ...     'subjects',
    ...     q({'relationshiptype': rels['has the role of'],
    ...       'objects': roles['Project Manager'],
    ...       'getContext': projects['zope.org redesign']}))]
    []
