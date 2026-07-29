Language guide
==============

Current ``1.x`` grammar
-----------------------

The parser and this guide use the same pest grammar.  The file embedded below
is the normative source for accepted ``1.x`` syntax; it is not a copy that can
drift away from the engine.

.. literalinclude:: ../../src/oneroll/grammar.pest
   :language: text
   :caption: src/oneroll/grammar.pest

Syntax acceptance is only one part of the language contract.  The executable
examples and behavior classifications in :doc:`conformance` define current
semantics, including compatibility-sensitive modifier behavior and the known
flat arithmetic precedence defect.

Current arithmetic
------------------

Scalar literals, dice values, intermediate totals, and collection sums use
signed 64-bit integers.  Addition, subtraction, multiplication, division,
exponentiation, and aggregation are checked: they never wrap and never expose
a Rust panic through Python.  Integer division truncates toward zero.

The current v1 exponent token remains ``^``.  A negative exponent or one above
``u32::MAX`` fails with ``arithmetic.invalid_exponent``; division by zero uses
``arithmetic.divide_by_zero``; every checked overflow uses
``arithmetic.overflow``.  ``0 ^ 0`` is defined as ``1``.  RFC-0001 changes the
strict-v2 exponent token to ``**`` without changing these numeric boundaries.

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
programs containing more than 1,000 instructions; configurable workload limits
are part of the production engine work.

Target ``2.0`` language
-----------------------

The target language adds typed values, ranges, weighted-list dice, variables,
validators, transformation options, functions, and conditional blocks.  Its
normative review contract and migration decisions live in :doc:`rfc-0001`.
Syntax shown there is a target contract unless its implementation-status table
marks a feature implemented.

The versioned ``ProgramResult``, typed Value union, normalized RollNode pool,
trace DAG, and structured error envelope are frozen for review in
:doc:`rfc-0003`.  They are target v2 contracts; the current ``roll`` and ``run``
dictionaries remain the compatibility API until their implementation issues
land.

Important compatibility decisions are:

* ``**`` is the v2 exponent operator; ``^`` is reserved for validator XOR.
* Strings are quoted and escaped rather than parsed with a greedy wildcard.
* ``help`` and ``la`` are CLI commands, not core-language expressions.
* ``@`` is reserved until bounded, auditable jump semantics are accepted.
* A trailing comment describes the whole program.  Per-instruction metadata is
  a future explicit construct rather than an ambiguous inline comment.
