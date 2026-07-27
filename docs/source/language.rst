Language guide
==============

Current ``1.x`` syntax
----------------------

The installed engine currently accepts numeric literals, ``XdY`` numeric dice,
parentheses, the arithmetic operators ``+``, ``-``, ``*``, ``/``, and ``^``, a
trailing ``#`` comment, and these parsed modifier forms:

.. code-block:: text

   !  e  K<number>  r<number>  ro<number>  R<number>  a<number>
   k<number>  kh<number>  kl<number>  dh<number>  dl<number>
   u  s  c<number>

This list describes accepted syntax, not a promise that every modifier already
has its final v2 semantics.  In particular, arithmetic currently has flat
precedence and some modifier combinations remain compatibility-sensitive.

Programs
--------

A program contains one or more instructions separated by ``;`` and may have
one trailing comment:

.. code-block:: text

   1d20 + 5; 2d6; 1d8 # encounter

Python exposes programs separately so the legacy single-result API remains
stable:

.. code-block:: python

   import oneroll

   single = oneroll.roll("1d20 + 5 # attack")
   program = oneroll.run("1d20 + 5; 2d6 # encounter")

``run`` returns ``{"results": [...], "comment": "..."}``.  Empty
instructions such as ``1d6;`` or ``1d6;;2d6`` are invalid.  All instructions
share one generated-face budget, so splitting an expensive calculation across
``;`` does not bypass resource limits.  The current safe default also rejects
Programs containing more than 1,000 instructions; configurable workload limits
are part of the production Engine work.

Target ``2.0`` language
-----------------------

The target language adds typed values, ranges, weighted-list dice, variables,
validators, transformation options, functions, and conditional blocks.  Its
normative draft and migration decisions live in :doc:`rfc-0001`.  Syntax shown
there is a target contract unless its status table marks a feature implemented.

Important compatibility decisions are:

* ``**`` is the v2 exponent operator; ``^`` is reserved for validator XOR.
* Strings are quoted and escaped rather than parsed with a greedy wildcard.
* ``help`` and ``la`` are CLI commands, not core-language expressions.
* ``@`` is reserved until bounded, auditable jump semantics are accepted.
* A trailing comment describes the whole program.  Per-instruction metadata is
  a future explicit construct rather than an ambiguous inline comment.
