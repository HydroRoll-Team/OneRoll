.. _rfc-0001:

RFC-0001: OneRoll Program Language v2
=====================================

:Status: Draft
:Target: OneRoll 2.0
:Discussion: https://github.com/HydroRoll-Team/OneRoll/issues/7
:Last updated: 2026-07-27

Summary
-------

OneRoll v2 is a small, pure, bounded language for dice and weighted-list
evaluation.  A ``Program`` contains ordered ``Instruction`` values; an
instruction evaluates an expression and then applies zero or more typed options.
The same AST and execution contract must serve Rust, Python, and the CLI.

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
   An expression followed by a left-to-right option pipeline.  Each option
   declares the input value kinds it accepts and the output kind it produces.

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

This is the normative syntax direction.  Rules may be split across Pest files,
but accepted strings and parse-tree meaning must remain equivalent.  Semantic
validation enforces type-specific constraints that syntax alone cannot express.

.. code-block:: peg

   WHITESPACE = _{ " " | "\t" | NEWLINE }

   program = { SOI ~ instruction ~ (instruction_separator ~ instruction)* ~ comment? ~ EOI }
   instruction_separator = _{ ";" }
   instruction = { expression ~ option* }
   comment = @{ "#" ~ (!NEWLINE ~ ANY)* }

   expression = { prefix_operator* ~ primary ~ (scalar_operator ~ prefix_operator* ~ primary)* }
   primary = _{
       parenthesized
     | function_call
     | dice
     | range
     | values_list
     | dynamic_variable
     | number
     | string
   }
   parenthesized = { "(" ~ expression ~ ")" }

   scalar_operator = { exponent | multiply | divide | add | subtract }
   exponent = { "**" }
   multiply = { "*" }
   divide = { "/" }
   add = { "+" }
   subtract = { "-" }
   prefix_operator = { "+" | "-" }

   number = @{ ASCII_DIGIT+ }
   signed_number = @{ ("+" | "-")? ~ ASCII_DIGIT+ }
   string = @{ "\"" ~ ("\\" ~ ANY | !"\"" ~ ANY)* ~ "\"" }
   identifier = @{ (ASCII_ALPHA_LOWER | "_") ~ (ASCII_ALPHANUMERIC | "_")* }
   dynamic_variable = @{ "${" ~ (identifier | ASCII_DIGIT+) ~ "}" }

   range = { "[" ~ signed_number ~ ".." ~ signed_number ~ "]" }
   values_list = { "[" ~ (scalar_operand ~ ("," ~ scalar_operand)*)? ~ "]" }
   scalar_operand = _{ dynamic_variable | signed_number }

   dice = _{ numeric_dice | list_dice }
   numeric_dice = { scalar_operand? ~ ^"d" ~ unique_value? ~ (number | range) }
   list_dice = { scalar_operand? ~ ^"l" ~ unique_value? ~ list_parameter }
   unique_value = { "u" }
   list_parameter = { "[" ~ weighted_item ~ ("," ~ weighted_item)* ~ "]" }
   weighted_item = { string ~ probability? }
   probability = { "[" ~ percentage ~ "]" }
   percentage = @{ ASCII_DIGIT+ ~ "%"? }

   function_call = _{ repeat_call }
   repeat_call = {
       ^"repeat" ~ "(" ~ scalar_operand ~ ";" ~ instruction ~ (";" ~ instruction)* ~ ")"
   }

   option = _{
       keep_and_explode
     | reroll_until
     | reroll_and_add
     | keep
     | filter
     | sort
     | count
     | reroll
     | explode
     | merge
     | bind
     | occurrences
     | unique
     | paint
     | conditional
     | split
     | group
   }

   ascending = { "l" }
   keep = { "k" ~ ascending? ~ number }
   keep_and_explode = { "K" ~ ascending? ~ number }
   filter = { "f" ~ validator_list }
   sort = { "s" ~ ascending? }
   count = { "c" ~ validator_list }
   reroll = { "r" ~ validator_list }
   reroll_until = { "R" ~ validator_list }
   reroll_and_add = { "a" ~ validator_list }
   explode = { "e" ~ validator_list }
   merge = { "m" ~ ("(" ~ expression ~ ")")? }
   bind = { "b" }
   occurrences = { "o" ~ number ~ ("," ~ (number | validator_list))? }
   unique = { "u" }
   paint = { "p" ~ "[" ~ color_count ~ ("," ~ color_count)* ~ "]" }
   color_count = { color ~ ":" ~ number }
   color = @{ "#" ~ ASCII_HEX_DIGIT{6} | identifier }
   conditional = { "i" ~ compare_scope? ~ validator_list ~ block ~ block? }
   block = { "{" ~ instruction ~ "}" }
   split = { "y" }
   group = { "g" ~ number }

   validator_list = { "[" ~ compare_scope? ~ predicate ~ (logic_operator ~ predicate)* ~ "]" }
   compare_scope = { "*" | ":" | "." }
   logic_operator = { "&" | "^" | "|" }
   predicate = _{ modulo_predicate | range | comparison }
   modulo_predicate = { "%" ~ scalar_operand ~ comparison }
   comparison = { compare_operator? ~ operand }
   compare_operator = { ">=" | "<=" | "!=" | "=" | ">" | "<" }
   operand = _{ dynamic_variable | signed_number | string }

Parser and precedence contract
------------------------------

Pest recognizes token order; a Pratt parser or equivalent AST builder enforces
precedence.  From strongest to weakest the v2 order is:

1. parenthesized expressions and primary values;
2. exponent ``**`` (right associative);
3. unary ``+`` and ``-``;
4. multiplication and division (left associative);
5. addition and subtraction (left associative).

Options bind after the complete expression and execute left to right.  Longer
prefixes must appear before shorter prefixes in Pest ordered choices.  For
example ``R`` and ``r`` are distinct, and legacy ``ro`` must be recognized
before ``r`` during migration parsing.

Value model
-----------

The runtime value union is conceptually:

.. code-block:: text

   Scalar(i64)
   Text(String)
   Values(List<Value>)
   RollSet(List<RollNode>)
   Boolean(bool)

Arithmetic accepts scalar-compatible values only.  Collection options operate
on ``Values`` or ``RollSet`` and return a declared kind.  Invalid combinations
are validation errors before random evaluation begins.  Checked ``i64``
arithmetic is required; overflow is never a panic or silent wrap.

Variables
---------

``${name}`` addresses a named variable whose identifier follows the QML-like
lowercase/underscore rule.  ``${0}`` addresses a positional argument.  Free-form
labels are runtime metadata and are not identifiers; allowing ``.*`` inside a
variable token would make ``}`` and comments ambiguous.

Variables are immutable during one program in v2.0.  A host supplies them when
constructing an Engine execution request.  Assignment syntax is out of scope.

Dice sources
------------

``D`` draws numeric values.  ``2d6`` retains v1 compatibility, while ranges
allow forms such as ``2d[1..6]``.  ``L`` draws from quoted values, for example:

.. code-block:: text

   2L["heads", "tails"]
   1L["common"[80%], "rare"[20%]]

Weights must be non-negative and have a positive total.  The engine normalizes
integer weights; it does not use floating-point probability during sampling.
``u`` on a dice source means sampling without replacement and therefore requires
a finite source and a count no larger than the source cardinality.

The original sketch allowed a range where a probability weight appears, but did
not define whether that range is sampled, normalized, or interpreted as an
interval.  V2.0 rejects that form; RFC-0006 may define it later if it has a
reproducible probability meaning.

Validators
----------

The optional leading scope token has these meanings:

* no token: evaluate each item independently;
* ``*``: all items must satisfy the predicate;
* ``.``: any item may satisfy the predicate;
* ``:``: validate the scalar projection of the node.

``&``, ``^``, and ``|`` mean AND, XOR, and OR.  They are left associative in
v2.0 unless parentheses are added to a later validator grammar.  Comparators are
longest-first Pest choices.  An omitted comparator means equality.

Options
-------

Options form a typed, left-to-right transformation pipeline.  Source-generating
options such as reroll and explode consume the shared evaluation budget and add
nodes to the trace.  Selection options never erase their provenance.

The draft normalizes three ambiguous forms from the original sketch:

* occurrences receives an explicit ``o`` prefix;
* merge arguments require parentheses;
* painter is named ``paint`` consistently and color/count pairs use ``:``.

Detailed input/output kinds and edge cases for each option must be frozen in
normative conformance cases before implementation.  ``bind`` and ``paint`` are
especially dependent on the trace/result RFC and may not ship merely because
their tokens parse.

Functions, conditionals, and jumps
----------------------------------

``repeat(count; instruction; ...)`` takes a scalar-compatible count followed by
one or more instructions.  Its iteration count and output cardinality consume
workload budgets.  Conditional ``i`` applies one required block and one optional
else block.

``@`` is reserved.  Backward jumps can create cycles and make static resource
analysis unreliable, so v2.0 must reject the token until a separate decision
defines a bounded, auditable meaning.  Structured ``repeat`` and ``if`` cover
the initial control-flow requirement.

Commands
--------

``help`` and ``la`` belong to the CLI command router.  They inspect client state
and are not valid core programs, keeping Engine evaluation pure and identical in
Rust, Python, services, and the CLI.

Compatibility
-------------

``roll(expression)`` remains the compatibility entry point and accepts exactly
one instruction.  ``run(program)`` returns an ordered program result.  Lowercase
``d`` remains accepted.  V1 ``^`` exponent, numeric modifier shorthand, ``!``,
``kh``, ``ro``, ``dh``, and ``dl`` require explicit compatibility cases and
actionable v2 replacements.

Comments are trailing program metadata.  A v1 single-expression comment remains
visible on the legacy ``roll`` result.  Empty instructions and trailing
semicolons are errors rather than silently ignored input.

Implementation status
---------------------

Implemented as a forward-compatible slice:

* non-empty programs separated by ``;``;
* ordered Rust/Python execution and CLI rendering;
* one shared generated-face budget and a 1,000-instruction default limit;
* single-expression ``roll`` compatibility and trailing comments.

Not yet implemented:

* the typed value union and spanned AST;
* v2 arithmetic precedence and ``**``;
* range and weighted-list dice;
* variables, validators, the complete option pipeline, functions, and blocks;
* structured traces, deterministic seeded randomness, and compatibility mode.

Delivery map
------------

* `#38 Program execution <https://github.com/HydroRoll-Team/OneRoll/issues/38>`_
* `#39 typed values, ranges, and variables <https://github.com/HydroRoll-Team/OneRoll/issues/39>`_
* `#40 numeric/range/list dice <https://github.com/HydroRoll-Team/OneRoll/issues/40>`_
* `#41 Validator contract <https://github.com/HydroRoll-Team/OneRoll/issues/41>`_
* `#42 collection transformation options <https://github.com/HydroRoll-Team/OneRoll/issues/42>`_
* `#43 repeat and conditional blocks <https://github.com/HydroRoll-Team/OneRoll/issues/43>`_

Acceptance criteria
-------------------

This RFC can move from Draft to Accepted only when:

* each rule has normative success and error examples;
* option input/output kinds and composition semantics are complete;
* every v1 syntax difference has a migration classification;
* the conformance corpus can run against Rust and the installed Python package;
* RFC-0002 and RFC-0003 agree on budgets, randomness, trace, and errors;
* RFC-0004 agrees on ``Engine.run`` and result typing.
