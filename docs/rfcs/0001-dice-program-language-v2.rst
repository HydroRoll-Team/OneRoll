.. _rfc-0001:

RFC-0001: OneRoll Program Language v2
=====================================

:Status: Review
:Target: OneRoll 2.0
:Discussion: https://github.com/HydroRoll-Team/OneRoll/issues/7
:Last updated: 2026-07-29

Summary
-------

OneRoll v2 is a small, pure, bounded language for dice and weighted-list
evaluation.  A ``Program`` contains ordered ``Instruction`` values.  Each
instruction evaluates an expression whose primary values may flow through
typed, left-to-right option pipelines.  The same AST and execution contract
must serve Rust, Python, and the CLI.

The original design sketch is intentionally not copied verbatim.  Pest is a PEG
with ordered choice, so empty productions, greedy strings, duplicated rules,
and prefix-overlapping tokens need explicit resolution.  This RFC records those
resolutions before the feature surface expands.

Goals
-----

* Parse every accepted input into a typed, spanned AST.
* Keep evaluation deterministic when a seed is supplied.
* Bound generated faces, AST depth, collection size, instruction count, and
  function expansion under one execution budget.
* Preserve a trace explaining source values, transformations, and totals.
* Provide a migration path for every supported v1 expression.

Non-goals
---------

* General-purpose mutation, filesystem/network access, or arbitrary Python.
* Unbounded loops or jumps.
* Treating CLI commands as reproducible language expressions.
* Exact probability analysis for every program; RFC-0006 defines that subset.

Semantic layers
---------------

The implementation must preserve these boundaries:

``Program``
   An ordered, non-empty list of instructions plus optional trailing metadata.
   All instructions share execution configuration, variables, RNG, and budgets.

``Instruction``
   One expression.  A pipeline attaches to the immediately preceding primary;
   parentheses make a compound expression into a primary.  Each option declares
   the input value kinds it accepts and the output kind it produces.

``Expression``
   A typed value-producing tree: scalar, text, collection, roll set, boolean,
   function result, or parenthesized expression.

``Validator``
   A pure predicate with an explicit scope.  Validators do not generate random
   values and cannot mutate the environment.

``Trace``
   The auditable record of source draws, option applications, discarded values,
   errors, and canonical expression text.  A numeric ``total`` is a projection,
   not the sole runtime value.

Target Pest grammar
-------------------

The target grammar is a real pest source file, parsed by a Rust contract test.
It is embedded rather than copied so the RFC and machine-checked source cannot
drift.  Semantic validation enforces type and cardinality constraints that
syntax alone cannot express.

.. literalinclude:: ../rfcs/0001-v2-target.pest
   :language: text
   :caption: docs/rfcs/0001-v2-target.pest

Parser and precedence contract
------------------------------

Pest recognizes token order; a Pratt parser or equivalent AST builder enforces
precedence.  From strongest to weakest the v2 order is:

1. parenthesized expressions and primary pipelines;
2. exponent ``**`` (right associative);
3. unary ``+`` and ``-``;
4. multiplication and division (left associative);
5. addition and subtraction (left associative).

An option binds to the immediately preceding primary and options on that
primary execute left to right.  Parentheses are required to transform a whole
compound expression: ``(1 + 2)i:[>2]{10}`` applies the conditional to ``3``,
while ``1 + 2i:[>2]{10}`` applies it only to ``2``.  Longer prefixes appear
before shorter prefixes in pest ordered choices.  Compatibility parsing
recognizes legacy ``ro`` before ``r``.

Normative arithmetic examples are:

.. list-table:: Arithmetic and binding examples
   :header-rows: 1
   :widths: 30 22 48

   * - Source
     - Result
     - Rule
   * - ``2 + 3 * 4``
     - ``14``
     - multiplication binds before addition
   * - ``2 ** 3 ** 2``
     - ``512``
     - exponentiation is right associative
   * - ``-2 ** 2``
     - ``-4``
     - exponentiation binds before unary minus
   * - ``(-2) ** 2``
     - ``4``
     - parentheses override precedence
   * - ``5 / 2``
     - ``2``
     - integer division truncates toward zero

Division by zero, a negative exponent, an exponent above ``u32::MAX``, and any
checked ``i64`` overflow are evaluation errors.  ``0 ** 0`` is defined as ``1``
for deterministic integer arithmetic.

Value model
-----------

The runtime value union is conceptually:

.. code-block:: text

   Scalar(i64)
   Text(String)
   Values(List<Value>)
   RollSet(List<RollNode>)
   Boolean(bool)

``Values`` may be nested by transformations such as ``occurrences``, ``group``,
and ``repeat``; source literals remain flat.  Every ``RollNode`` has a stable
trace identity, a typed current value, its complete source-draw chain, retained
state, and presentation annotations.  Paint and selection alter annotations or
retained state without replacing that identity.

Arithmetic accepts scalar-compatible values only and every scalar operator
returns ``Scalar``.  ``Scalar`` projects to itself.  A flat ``Values`` or
``RollSet`` containing only scalars projects to its checked sum; the empty
scalar collection projects to zero.  Operand source nodes remain in the trace,
but the arithmetic result is not a collection.  Text, Boolean, nested, or mixed
collections have no scalar projection.  Collection options operate on
``Values`` or ``RollSet`` and return the declared kind in the option matrix.
Invalid combinations are validation errors before the first random word is
consumed.  Use ``m(expr)`` rather than arithmetic to combine collections for a
later collection option.

Equality is defined for values of the same kind.  Ordering is defined only for
homogeneous scalar or text collections; text uses Unicode scalar-value order.
No implicit parsing of text, Boolean-to-integer conversion, or flattening of
nested values occurs.

Variables
---------

``${name}`` addresses a named variable.  Its first character is lowercase ASCII
or ``_``; subsequent characters are ASCII alphanumeric or ``_``.  ``${0}``
addresses a positional argument.  Free-form labels are runtime metadata and are
not identifiers; allowing ``.*`` inside a variable token would make ``}`` and
comments ambiguous.

Variables are immutable during one program in v2.0.  A host supplies them when
constructing an Engine execution request.  Assignment syntax is out of scope.
Inside a conditional block, lexical ``${0}`` is the condition subject and
shadows request positional zero for that block only.  Other variables retain
their outer immutable bindings.

Dice sources
------------

``d`` draws numeric values.  ``2d6`` retains v1 compatibility, while ranges
allow forms such as ``2d[1..6]``.  ``L`` draws from quoted text, for example:

.. code-block:: text

   2L["heads", "tails"]
   1L["common"[80%], "rare"[20%]]

The count defaults to one, must have a scalar projection greater than zero, and
is checked against ``source_items`` before allocation.  Numeric sides must be
positive.  Inclusive ranges require lower bound less than or equal to upper
bound and compute cardinality with checked arithmetic.  Empty list-dice sources
are syntax errors; an empty value literal ``[]`` remains valid.

One list uses exactly one weight mode:

Uniform
   No item has an annotation; every distinct text value has weight one.

Integer weight
   At least one item has ``[n]`` and no item has ``%``.  Unannotated items have
   weight one.  Weights are non-negative and the checked total is positive.

Percentage
   Every item has ``[n%]``.  Each value is between 0 and 100 inclusive and the
   checked total is exactly 100.  Percentage and integer-weight annotations
   cannot be mixed.

Sampling always uses normalized integers and never floating point.  Equal text
items are combined by adding their weights before sampling.  ``u`` immediately
after ``d`` or ``L`` means sampling without replacement by resulting value; the
selected value and its weight are removed before the next draw.  The count may
not exceed the finite distinct source cardinality.  Postfix option ``u`` is
different: it removes duplicates after ordinary sampling and never refills.

The original sketch allowed a range where a probability weight appears, but did
not define whether that range is sampled, normalized, or interpreted as an
interval.  V2.0 rejects that form; RFC-0006 may define it later if it has a
reproducible probability meaning.  The canonical source tokens are lowercase
``d`` and uppercase ``L``; parsing is ASCII-case-insensitive for compatibility.

Validators
----------

The optional scope token precedes the validator list and has these meanings:

* no token: evaluate each item independently and produce a decision mask;
* ``*``: all items must satisfy the predicate;
* ``.``: any item may satisfy the predicate;
* ``:``: validate the scalar projection of the complete input.

Each-scope validators are accepted by selection, count, and source-generating
options.  Aggregate scopes are accepted only by conditional ``i``; using them
where an item mask is required is ``validation.invalid_scope``.  On a scalar or
text input, each scope evaluates one item.  All and any over an empty collection
are true and false respectively; scalar scope on a value without a scalar
projection is an error.

``&``, ``^``, and ``|`` mean AND, XOR, and OR.  They share one precedence level
and associate left to right.  AND and OR short-circuit; XOR evaluates both
sides.  Comparators are longest-first pest choices.  An omitted comparator means
equality.  Ordering requires matching ordered kinds.  A range predicate such as
``[1..6]`` is inclusive.  ``%2=0`` applies checked remainder before comparison;
a zero divisor is ``validation.zero_modulus``.  ``min`` and ``max`` name the
bounds of a finite source-backed ``RollSet`` and are invalid for other inputs.

Examples include ``f[!=6]``, ``c[>=8&<=10]``, ``R[<=2]``, and
``i.[=max]{"critical"}{"ordinary"}``.  Empty lists, wrong-kind comparisons,
unknown variables, and an invalid scope fail during validation before random
evaluation.

Options
-------

Options form a typed, left-to-right transformation pipeline.  Source-generating
options such as reroll and explode consume the shared evaluation budget and add
nodes to the trace.  Selection options never erase their provenance.

The normative option contract is:

.. list-table:: Typed option matrix
   :header-rows: 1
   :widths: 14 24 24 38

   * - Form
     - Accepted input
     - Output
     - Effect and validation
   * - ``kN``, ``klN``
     - ordered flat ``Values`` or ``RollSet``
     - same kind
     - stably retain the highest or lowest ``N`` items; ``1 <= N <= len``
   * - ``dN``, ``dlN``
     - ordered flat ``Values`` or ``RollSet``
     - same kind
     - stably discard the highest or lowest ``N`` items; ``1 <= N <= len``
   * - ``KN``, ``KlN``
     - finite numeric source ``RollSet``
     - ``RollSet``
     - recursively explode on source ``max``, then apply ``kN`` or ``klN``
   * - ``fV``
     - flat ``Values`` or ``RollSet``
     - same kind
     - retain items whose each-scope validator ``V`` is true
   * - ``s``, ``sl``
     - ordered homogeneous flat collection
     - same kind
     - stable high-to-low or low-to-high sort
   * - ``cV``
     - flat ``Values`` or ``RollSet``
     - ``Scalar``
     - count items whose each-scope validator ``V`` is true
   * - ``rV``
     - finite source-backed ``RollSet``
     - ``RollSet``
     - redraw each matching node exactly once and replace its current value
   * - ``RV``
     - finite source-backed ``RollSet``
     - ``RollSet``
     - redraw and replace while each newly drawn value still matches
   * - ``aV``
     - finite numeric source ``RollSet``
     - ``RollSet``
     - redraw each matching node once and add the draw to its current value
   * - ``eV``
     - finite numeric source ``RollSet``
     - ``RollSet``
     - recursively draw and add while the newest draw matches
   * - ``m(expr)``
     - flat ``Values`` or ``RollSet``
     - same kind
     - evaluate ``expr`` once at this pipeline point and append a compatible collection
   * - ``b``
     - flat ``Values`` or ``RollSet``
     - same kind
     - prepend compatible values from all earlier instructions without altering their results
   * - ``o``, ``o(N,S)``
     - homogeneous flat collection
     - nested ``Values``
     - return ordered ``[value, count]`` entries meeting minimum count ``N`` and selector ``S``
   * - ``u``
     - flat ``Values`` or ``RollSet``
     - same kind
     - retain the first item for each equal value, without replacement draws
   * - ``p[color:N,...]``
     - ``RollSet``
     - ``RollSet``
     - annotate consecutive retained nodes with normalized colors
   * - ``iV{yes}{no}``
     - any value accepted by scoped validator ``V``
     - branch-dependent
     - run the selected instruction block; missing ``no`` means identity
   * - ``y``
     - ``Values`` or ``RollSet``
     - same kind
     - flatten one nested Values level or spread compound source draws into sibling nodes
   * - ``gN``
     - flat ``Values`` or ``RollSet``
     - nested ``Values``
     - form consecutive groups of width ``N`` and retain a final short remainder group

All selection and ordering operations are stable: equal items keep source order,
and discarded items remain visible in the trace.  A keep, drop, paint, or group
count of zero is invalid.  Oversized keep, drop, or paint counts are errors
rather than silent truncation.  Group width may exceed collection length and
then produces one remainder group.  Empty input remains empty for filter, sort,
count, occurrences, unique, split, and group.

``K`` is atomic at the language level but its trace contains an ``explode`` node
followed by a ``keep`` node.  Explosion adds each accepted draw to the same
logical roll node; ``y`` exposes those component draws as siblings without
changing their checked scalar sum.  ``r`` and ``R`` replace the current value,
while ``a`` and ``e`` add to it.  Every attempted draw uses RFC-0002 counters;
impossible ``R`` or ``e`` conditions terminate with a resource error.

``m(expr)`` replaces the ambiguous bare merge form.  Its argument may generate
random values and therefore evaluates exactly when the option is reached.
``b`` is the only history-aware option: it reads completed earlier instruction
values in source order, never future values, and never deletes or rewrites the
``ProgramResult`` instruction array.  It requires at least one prior compatible
collection.  Both forms preserve source instruction and node identity in the
trace.

Occurrences uses ``o`` as the unambiguous prefix.  Bare ``o`` means minimum
count one.  ``o(2)`` requires two occurrences, ``o(2,7)`` additionally requires
scalar value at least seven, and ``o(2,[<6])`` uses an each-scope selector.
Entries sort by scalar or text value ascending.  Each logical entry is a nested
``Values([value, Scalar(count)])`` value; RFC-0003 owns its serialized envelope.

Paint pairs use canonical ``color:count`` order.  Counts address consecutive
retained nodes, so ``p[red:2,blue:1]`` paints the first two red and the next one
blue.  Named colors are lowercase identifiers; hexadecimal colors canonicalize
to lowercase ``#rrggbb``.  Painting changes presentation metadata only.

Functions, conditionals, and jumps
----------------------------------

``repeat(count; instruction; ...)`` takes a scalar-compatible, non-negative
count followed by one or more instructions.  It returns one nested ``Values``
entry per iteration, containing body values in instruction order.  Count zero
returns empty ``Values`` without activating the body.  Every iteration and body
instruction consumes the request's execution, nesting, work, output, and random
budgets; body failure atomically fails the complete Program.

Conditional ``i`` takes a scoped validator, one required true block, and one
optional false block.  Aggregate scopes run exactly one selected block against
the complete input.  Each scope maps the collection in source order; each block
must return one atom of the subject kind, and the outer collection kind is
preserved.  Lexical ``${0}`` contains the current subject.  If the false block
is absent, a false subject retains its input unchanged.  No branch is evaluated
speculatively, and a selected branch uses the same context, RNG, and counters.

For example, ``4d6i[<3]{${0}+1}`` increments only low faces, while
``4d6i.[=max]{"critical"}{"ordinary"}`` returns one aggregate text result.

``@`` is reserved.  Backward jumps can create cycles and make static resource
analysis unreliable, so v2.0 must reject the token until a separate decision
defines a bounded, auditable meaning.  Structured ``repeat`` and ``if`` cover
the initial control-flow requirement.

Commands
--------

``help`` and ``la`` belong to the CLI command router.  They inspect client state
and are not valid core programs, keeping Engine evaluation pure and identical in
Rust, Python, services, and the CLI.

Canonical text
--------------

Canonical rendering is syntax, not presentation.  It uses lowercase ``d`` for
numeric dice, uppercase ``L`` for list dice, lowercase option tokens except
``K`` and ``R``, one space around scalar operators, one space after commas and
semicolons, and no whitespace between a primary and its options.  Strings use
double quotes and only ``\"``, ``\\``, ``\n``, ``\r``, and ``\t`` escapes.
Named colors and hexadecimal digits are lowercase.  Parentheses are emitted
whenever required to preserve the typed AST, including a pipeline applied to a
compound expression.  A comment is separated by one space and belongs to the
complete Program.

Examples of canonical text include:

.. code-block:: text

   2d6 + 3
   2du[1..6]
   1L["common"[80%], "rare"[20%]]
   4d6e[=max]k3
   1d6m(2d6)k1
   repeat(3; 1d6; 1L["yes", "no"])
   1d20 + 5; 2d6 # encounter

Normative syntax and error cases
--------------------------------

The option matrix and the following cases define at least one success and one
failure boundary for every public syntax family.  Child implementation issues
must copy these case identifiers into the executable v2 conformance corpus
rather than inventing a second contract.

.. list-table:: Normative language cases
   :header-rows: 1
   :widths: 24 34 42

   * - Case identifier
     - Source
     - Required result
   * - ``program.multiple``
     - ``1d6; 2d6 # encounter``
     - two ordered results and one Program comment
   * - ``program.empty``
     - empty source
     - ``parse.empty_program``
   * - ``program.empty_instruction``
     - ``1d6;;2d6`` or ``1d6;``
     - ``parse.empty_instruction``
   * - ``string.escaped``
     - ``"say \"yes\"\nnow"``
     - one Text value containing a quote and newline
   * - ``string.unterminated``
     - ``"unfinished``
     - spanned ``parse.invalid_syntax``
   * - ``boolean.literal``
     - ``true`` or ``false``
     - one Boolean value with canonical lowercase text
   * - ``variable.named``
     - ``${bonus} + 2``
     - checked scalar result when ``bonus`` is Scalar
   * - ``variable.unknown``
     - ``${missing}``
     - ``validation.unknown_variable``
   * - ``range.inclusive``
     - ``[-1..1]``
     - ``Values([-1, 0, 1])``
   * - ``range.reversed``
     - ``[2..1]``
     - ``validation.invalid_range``
   * - ``values.empty``
     - ``[]``
     - empty Values with scalar projection zero
   * - ``dice.numeric``
     - ``2d6``
     - two numeric source nodes in ``1..6``
   * - ``dice.invalid_count``
     - ``0d6``
     - ``validation.invalid_source_count``
   * - ``dice.unique_list``
     - ``2Lu["yes", "no"]``
     - two different Text source values
   * - ``weight.percent``
     - ``1L["a"[75%], "b"[25%]]``
     - integer weighted sampling with total 100
   * - ``weight.mixed``
     - ``1L["a"[1], "b"[50%]]``
     - ``validation.weight_mode``
   * - ``validator.modulo``
     - ``4d6c[%2=0]``
     - Scalar count of even faces
   * - ``validator.empty``
     - ``4d6c[]``
     - spanned ``parse.invalid_syntax``
   * - ``pipeline.compound``
     - ``(1 + 2)i:[>2]{10}``
     - apply the conditional to the compound Scalar result
   * - ``merge.bare``
     - ``1d6m``
     - spanned ``parse.invalid_syntax``
   * - ``bind.no_history``
     - ``1d6b``
     - ``validation.invalid_bind``
   * - ``occurrences.filtered``
     - ``10d10o(2,[<6])``
     - ordered nested value/count entries
   * - ``paint.oversized``
     - ``2d6p[red:3]``
     - ``validation.invalid_count``
   * - ``conditional.aggregate``
     - ``2d10i:[>15]{"success"}{"fail"}``
     - exactly one selected Text branch
   * - ``repeat.zero``
     - ``repeat(0; 1d6)``
     - empty Values and no random draw
   * - ``jump.reserved``
     - ``@``
     - ``migration.reserved_jump``
   * - ``command.outside_language``
     - ``help`` or ``la``
     - CLI routing or ``parse.invalid_syntax`` in Engine input

Compatibility
-------------

``roll(expression)`` remains the v1 compatibility entry point throughout the
2.x support window and accepts exactly one instruction.  ``Engine.run`` and the
top-level ``run`` use strict v2 parsing in 2.0.  An explicit Engine compatibility
mode may run complete v1 Programs; it preserves recorded v1 behavior and emits
structured migration diagnostics.  No v1 form is silently given v2 semantics.
Removal of v1 mode is a 3.0-or-later decision.

.. list-table:: V1 migration matrix
   :header-rows: 1
   :widths: 24 28 48

   * - V1 form or behavior
     - Canonical v2
     - Compatibility rule
   * - flat binary precedence
     - mathematical precedence or parentheses
     - v1 mode preserves the recorded left-to-right AST
   * - ``^`` exponent
     - ``**``
     - v1 mode accepts ``^``; strict mode reports ``migration.v1_exponent``
   * - ``!`` or bare ``e``
     - ``e[=max]``
     - v1 mode preserves bounded maximum-face explosion
   * - ``rN`` or ``roN``
     - ``r[<=N]``
     - both recorded v1 forms redraw once
   * - ``RN``
     - ``R[<=N]``
     - repeated redraw remains request-budget bounded
   * - ``aN``
     - ``a[<=N]``
     - one matching redraw is added
   * - ``cN``
     - ``c[=N]``
     - count returns Scalar
   * - ``kN`` or ``khN``
     - ``kN``
     - v1 aliases remain accepted in v1 mode
   * - ``klN``
     - ``klN``
     - spelling and keep-low meaning are retained
   * - ``dhN``
     - ``dN``
     - compatibility parser reports the shorter replacement
   * - ``dlN``
     - ``dlN``
     - spelling and drop-low meaning are retained
   * - ``s`` ascending implementation
     - ``sl``
     - strict v2 ``s`` is descending; v1 mode preserves observed ascending order
   * - ``KN`` incomplete explosion
     - ``KN`` with atomic explode-then-keep semantics
     - v1 mode preserves the known defect; strict mode uses corrected semantics
   * - postfix ``u``
     - postfix ``u``
     - stable first-occurrence behavior is retained

Comments remain trailing Program metadata.  A v1 single-expression comment is
visible on the legacy ``roll`` result.  Empty instructions and trailing
semicolons remain errors.  Diagnostics include phase, span, construct, and the
canonical replacement; client code branches on their stable code rather than
localized message text.

Implementation status
---------------------

Implemented as a forward-compatible slice:

* non-empty programs separated by ``;``;
* ordered Rust/Python execution and CLI rendering;
* one shared generated-face budget and a 1,000-instruction default limit;
* single-expression ``roll`` compatibility and trailing comments;
* a machine-checked pest source for the target v2 grammar.

Not yet implemented:

* the typed value union and spanned AST;
* v2 arithmetic precedence and ``**``;
* range and weighted-list dice;
* variables, validators, the complete option pipeline, functions, and blocks;
* structured traces, deterministic seeded randomness, and compatibility mode.

Delivery map
------------

* `#16 precedence and canonical expressions <https://github.com/HydroRoll-Team/OneRoll/issues/16>`_
* `#15 selection and query options <https://github.com/HydroRoll-Team/OneRoll/issues/15>`_
* `#24 source-generating options <https://github.com/HydroRoll-Team/OneRoll/issues/24>`_
* `#38 Program execution <https://github.com/HydroRoll-Team/OneRoll/issues/38>`_
* `#39 typed values, ranges, and variables <https://github.com/HydroRoll-Team/OneRoll/issues/39>`_
* `#40 numeric/range/list dice <https://github.com/HydroRoll-Team/OneRoll/issues/40>`_
* `#41 Validator contract <https://github.com/HydroRoll-Team/OneRoll/issues/41>`_
* `#42 collection transformation options <https://github.com/HydroRoll-Team/OneRoll/issues/42>`_
* `#43 repeat and conditional blocks <https://github.com/HydroRoll-Team/OneRoll/issues/43>`_
* `#29 v1 migration diagnostics <https://github.com/HydroRoll-Team/OneRoll/issues/29>`_

Cross-RFC dependencies
----------------------

RFC-0002 is accepted and owns the shared budget, random, cancellation, and
atomic-failure contract used here.  RFC-0003 must preserve this RFC's Value
kinds, nested Values, stable RollNode identity, instruction history, selected
and discarded provenance, color annotations, and structured migration errors.
RFC-0004 must expose strict-v2 ``Engine.run``, v1-compatible ``roll``, immutable
variables, compatibility mode, and the one-context execution boundary.

Those two RFCs may choose serialization and API shapes, but may not change this
language's accepted strings or option effects without amending RFC-0001.  Issue
#7 therefore remains in Review until RFC-0003 (#4) and RFC-0004 (#5) are
accepted; v2 implementation issues no longer need to wait for executable v2
cases to exist before the contract itself can be accepted.

Acceptance criteria
-------------------

This RFC can move from Review to Accepted only when:

* the checked target pest grammar and normative cases remain valid;
* option input/output kinds and composition semantics remain complete;
* every recorded v1 syntax difference retains a migration classification;
* each child implementation issue adopts the applicable normative case IDs for
  the future Rust/installed-Python v2 conformance corpus;
* accepted RFC-0002 and RFC-0003 agree on budgets, randomness, trace, and
  errors; and
* accepted RFC-0004 agrees on ``Engine.run``, compatibility mode, variables,
  and result typing.
