=======
Changes
=======

2.1 (2021-03-22)
================

- Add support for Python 3.7 up to 3.9.

- Update to ``zope.component >= 5``.


2.0.post1 (2018-06-19)
======================

- Fix PyPI page by using correct ReST syntax.


2.0 (2018-06-19)
================

The 2.x line is almost completely compatible with the 1.x line.
The one notable incompatibility does not affect the use of relationship
containers and is small enough that it will hopefully affect noone.

New Requirements
----------------

- zc.relation

Incompatibilities with 1.0
--------------------------

- ``findRelationships`` will now use the defaultTransitiveQueriesFactory if it
  is set.  Set ``maxDepth`` to 1 if you do not want this behavior.

- Some instantiation exceptions have different error messages.

Changes in 2.0
--------------

- the relationship index code has been moved out to zc.relation and
  significantly refactored there.  A fully backwards compatible subclass
  remains in zc.relationship.index

- support both 64-bit and 32-bit BTree families

- support specifying indexed values by passing callables rather than
  interface elements (which are also still supported).

- in findValues and findValueTokens, `query` argument is now optional.  If
  the query evaluates to False in a boolean context, all values, or value
  tokens, are returned.  Value tokens are explicitly returned using the
  underlying BTree storage.  This can then be used directly for other BTree
  operations.

  In these and other cases, you should not ever mutate returned results!
  They may be internal data structures (and are intended to be so, so
  that they can be used for efficient set operations for other uses).
  The interfaces hopefully clarify what calls will return an internal
  data structure.

- README has a new beginning, which both demonstrates some of the new features
  and tries to be a bit simpler than the later sections.

- `findRelationships` and new method `findRelationshipTokens` can find
  relationships transitively and intransitively.  `findRelationshipTokens`
  when used intransitively repeats the behavior of `findRelationshipTokenSet`.
  (`findRelationshipTokenSet` remains in the API, not deprecated, a companion
  to `findValueTokenSet`.)

- 100% test coverage (per the usual misleading line analysis :-) of index
  module.  (Note that the significantly lower test coverage of the container
  code is unlikely to change without contributions: I use the index
  exclusively.  See plone.relations for a zc.relationship container with
  very good test coverage.)

- Tested with Python 2.7 and Python >= 3.5

- Added test extra to declare test dependency on ``zope.app.folder``.


Branch 1.1
==========

(supports Zope 3.4/Zope 2.11/ZODB 3.8)

1.1.0
-----

- adjust to BTrees changes in ZODB 3.8 (thanks Juergen Kartnaller)

- converted buildout to rely exclusively on eggs

Branch 1.0
==========

(supports Zope 3.3/Zope 2.10/ZODB 3.7)

1.0.2
-----

- Incorporated tests and bug fixes to relationship containers from
  Markus Kemmerling:

  * ManyToOneRelationship instantiation was broken

  * The `findRelationships` method misbehaved if both, `source` and `target`,
    are not None, but `bool(target)` evaluated to False.

  * ISourceRelationship and ITargetRelationship had errors.

1.0.1
-----

- Incorporated test and bug fix from Gabriel Shaar::

    if the target parameter is a container with no objects, then
    `shared.AbstractContainer.isLinked` resolves to False in a bool context and
    tokenization fails.  `target and tokenize({'target': target})` returns the
    target instead of the result of the tokenize function.

- Made README.rst tests pass on hopefully wider set of machines (this was a
  test improvement; the relationship index did not have the fragility).
  Reported by Gabriel Shaar.

1.0.0
-----

Initial release
