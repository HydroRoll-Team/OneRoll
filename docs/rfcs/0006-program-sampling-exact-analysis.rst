.. _rfc-0006:

RFC-0006: Program Sampling and Exact Analysis Scope
===================================================

:Status: Draft
:Target: OneRoll 2.1
:Discussion: https://github.com/HydroRoll-Team/OneRoll/issues/3
:Last updated: 2026-07-29

Summary
-------

OneRoll 2.1 exposes two deliberately separate operations:

``Engine.sample``
   Executes a complete Program a requested number of times with RFC-0002
   deterministic randomness, shared resource limits, cancellation, and an
   explicit seed.  It returns observations and statistical estimates.

``Engine.analyze_exact``
   Symbolically enumerates one supported Instruction and returns a finite
   distribution whose probabilities are arbitrary-precision rational numbers.
   It accepts no seed and never samples.

An exact request either returns an exact distribution or a stable analysis
error.  OneRoll never silently substitutes Monte Carlo output, truncates a
distribution, drops low-probability outcomes, or treats a build timeout as an
approximation policy.

This RFC is a draft decision boundary for the issue 32 prototype and issue 33
human capability review.  The checked matrix records which constructs are
provisionally supported, bounded, or unsupported.  It is not a claim that an
exact-analysis engine exists in the current package.

Current baseline
----------------

The current 1.x compatibility package exposes ``roll_multiple`` and
``roll_statistics``.  They evaluate repeated samples under a shared request
budget and derive count, minimum, maximum, mean, total, and the raw scalar
results in Python.  They do not accept a public seed, return confidence
information, expose RFC-0003 typed results, support cancellation, or compute an
exact probability distribution.

The Rust evaluator already owns bounded batch execution and the
``oneroll-chacha12-v1`` request stream.  RFC-0004 defines the future typed,
atomic ``Engine.run_batch`` boundary and deterministic per-sample seed
derivation.  Sampling builds on that path; it does not preserve the current
Python aggregation loop as a second execution engine.

No exact analyzer is implemented today.  Public documentation and clients must
continue to call the existing feature “statistics” or “sampling,” never
“probability,” “odds,” or “exact analysis.”

Terminology
-----------

Sample
   One ordinary execution of the requested Program.  It has the same typed
   result, errors, trace semantics, budgets, and compatibility mode as
   ``Engine.run``.

Sampling
   A finite collection of samples.  Counts and summary statistics estimate an
   underlying distribution and carry sampling uncertainty.

Exact outcome
   One canonical ``AnalysisValue`` produced by a supported Instruction, paired
   with a reduced rational probability.  Scalar, text, Boolean, and nested
   Values retain their RFC-0003 shapes.  A RollSet contains materialized typed
   items and deterministic annotations instead of execution-node references.

Exact distribution
   A finite map from canonical typed values to exact outcome probabilities.
   Equal values are combined and all probabilities sum to exactly one.

State
   One intermediate typed value plus the analysis continuation needed to apply
   the remaining expression or option pipeline.  State count is an operational
   complexity measure, not the final support size.

Support size
   The number of distinct final typed values with non-zero probability.

Goals
-----

* Make sampling reproducible through the existing random and batch protocols.
* Make uncertainty and aggregation rules identical across Rust, Python, CLI,
  and TUI consumers.
* Define a useful finite exact subset without promising a general symbolic
  interpreter.
* Preserve typed values instead of reducing text, Boolean, list, or RollSet
  outcomes to integers, while avoiding fabricated execution nodes.
* Bound state growth, rational arithmetic, memory, and output before allocation.
* Return stable unsupported and too-complex errors through Rust and Python.
* Keep mode selection explicit at every API and user-interface boundary.

Non-goals
---------

* Exact analysis of every valid v2 Program.
* Approximate symbolic methods, floating-point probability tables, or pruning.
* Bayesian inference, hypothesis testing, or promises about a physical die.
* Inferring probability from display text or compatibility dictionaries.
* Treating a random seed as meaningful input to exact analysis.
* Returning partial exact distributions after cancellation or a limit failure.

API separation
--------------

The target public methods are conceptually:

.. code-block:: python

   sample = engine.sample(
       source,
       samples=100_000,
       variables=variables,
       seed=seed,
       cancellation=token,
       deadline=deadline,
   )

   exact = engine.analyze_exact(
       instruction,
       variables=variables,
       cancellation=token,
       deadline=deadline,
       policy=analysis_policy,
   )

``sample`` accepts a complete Program and always returns ``SampleResult``.
``analyze_exact`` accepts exactly one Instruction and always returns
``ExactDistribution``.  The methods do not share a mode flag, Boolean
``exact`` option, or result union.  This makes accidental approximation visible
in static typing, logs, CLI commands, and stored payloads.

Passing ``seed`` to exact analysis is an input error.  Requesting exact mode for
an unsupported construct is an analysis error.  Neither case invokes sampling
or initializes the RNG.

Normative API and error contract
--------------------------------

The checked contract freezes method identity, result fields, aggregation
rules, limits, cancellation, and stable error codes:

.. literalinclude:: ../rfcs/0006-analysis-contract.json
   :language: json
   :caption: docs/rfcs/0006-analysis-contract.json

Seeded sampling
---------------

Execution model
~~~~~~~~~~~~~~~

One sampling request creates one RFC-0002 request context.  It validates source,
variables, sample count, and static limits before deriving sample seeds.  Each
sample executes the complete Program with the RFC-0004
``oneroll-sha256-batch-v1`` sub-seed for its zero-based index.  Samples execute
in index order in v2.1.  A later parallel implementation must retain the same
sub-seeds, result order, counters, cancellation boundary, and summary bytes.

Every sample is an ordinary typed ``ProgramResult``.  The batch is atomic: a
parse, validation, entropy, budget, cancellation, deadline, arithmetic, or
serialization failure returns one structured error and no ``SampleResult``.
The failure identifies the root seed, zero-based sample index when execution
started, and consumed resource counters, as frozen by RFC-0003 and RFC-0004.

Sampling consumes ``batch_samples``, ``executed_instructions``,
``generated_values``, ``collection_items``, ``work_units``, ``output_items``,
``output_bytes``, deadline, and cancellation from the same context.  A helper,
CLI client, or renderer cannot reset counters between samples.

Summary contract
~~~~~~~~~~~~~~~~

``SampleResult`` contains the source, canonical Program, compatibility mode,
root random descriptor, requested/completed sample count, aggregation
descriptor, histogram, optional scalar statistics, and optionally the ordered
typed child results when the caller explicitly requests them and the output
budget permits it.

Histogram keys are canonical ``AnalysisValue`` JSON, not ``details`` text or
RollNode identifiers.  A sampled RFC-0003 RollSet is normalized by replacing
each RollReference with the referenced typed value and its deterministic
annotations; execution provenance remains available only in an included child
ProgramResult.  Counts are unsigned integers and probabilities are
``count / samples``.  Each entry includes a two-sided 95 percent Wilson score interval using
``z = 1.959963984540054``.  The method and confidence level are serialized so a
future method cannot silently change stored results.

Scalar statistics exist only when every top-level Instruction value has a
non-null scalar projection and the Program has exactly one Instruction.  They
are otherwise JSON null.  Numeric aggregation uses sample index order and a
specified stable online algorithm:

* ``mean`` is the IEEE-754 binary64 arithmetic mean;
* ``variance`` is the unbiased sample variance with denominator ``n - 1`` and
  is null for one sample;
* ``standard_error`` is ``sqrt(variance / n)`` and is null when variance is
  null; and
* quantiles at ``0.05``, ``0.25``, ``0.50``, ``0.75``, and ``0.95`` use the
  nearest-rank rule: sorted index ``ceil(p * n) - 1``.

The raw count/histogram is authoritative.  Floating summaries are convenience
estimates and serialize finite numbers only.  Checked conversion rejects a
sample projection that cannot be represented without violating the result
schema; infinities and NaNs are never emitted.

Reproducibility
~~~~~~~~~~~~~~~

Equal package compatibility contract, source, variables, policy, sample count,
root seed, and aggregation version produce byte-equivalent JSON apart from
explicit non-semantic metadata such as wall-clock duration.  Wall-clock timing
is excluded from the normative payload.

Unseeded sampling obtains one root seed from operating-system entropy and
returns it.  Replaying with that seed must reproduce the normative payload.
Entropy failure returns ``random.entropy_unavailable`` without a fallback seed.

Exact analysis model
--------------------

Input boundary
~~~~~~~~~~~~~~

Exact analysis accepts one strict-v2 Instruction.  A semicolon or second
Instruction returns ``analysis.unsupported.program_arity``.  This avoids
publishing per-instruction marginals that discard Program correlations or a
joint distribution whose state model changes when bind and control flow ship.
Full-Program sampling remains available.

Host variables are immutable deterministic RFC-0001 values.  They are copied,
validated, and charged before analysis.  A variable cannot itself contain a
probability distribution, callable, iterator, or lazy collection.

The analyzer parses and validates through the normal Engine front end.  It
builds a finite analysis plan only after the Instruction is valid and proven to
contain no possible runtime error under its input domains.  It does not execute
the ordinary random evaluator once per outcome.

Probability representation
~~~~~~~~~~~~~~~~~~~~~~~~~~

Every internal and public probability is a reduced arbitrary-precision
rational ``numerator / denominator`` with a non-negative numerator and positive
denominator.  Public numerator and denominator are decimal strings so the wire
contract is not limited by JSON integer or host-language bounds.

The implementation may use ``BigRational`` or an equivalent exact type.  It
must never derive an exact probability from binary floating point.  After each
combination, equal canonical AnalysisValues are merged and zero-probability
states are removed.  A successful distribution has at least one outcome and
sums exactly to one.

Each public outcome carries its canonical ``value``, a nullable signed 64-bit
``scalar`` projection, and its rational ``probability``.  The scalar field is
null for values without an ordinary scalar projection; it does not replace the
typed value or participate in outcome identity.

Arithmetic uses the runtime's checked signed 64-bit Value semantics.  An exact
request fails atomically with ``analysis.possible_runtime_error`` if any
reachable path can divide by zero, use an invalid exponent, overflow, or
otherwise produce an ordinary execution error.  V2.1 does not return mixed
value/error probability tables.

Dice sources
~~~~~~~~~~~~

Finite numeric dice and inclusive range dice assign equal rational probability
to each source value.  Counts, sides, and bounds must be statically known from
literals or deterministic variables before state expansion.

List dice reuse RFC-0001 weight normalization exactly:

* uniform items have weight one;
* integer-weight mode uses non-negative integer weights, with unannotated items
  receiving weight one and a positive checked total;
* percentage mode requires every item to use an integer percentage, each from
  zero through 100, with total exactly 100; and
* equal text values are combined by adding weights before drawing.

One draw selects value ``i`` with exact probability ``weight_i / total_weight``.
No alias table or floating threshold becomes part of the exact contract.

Without replacement
~~~~~~~~~~~~~~~~~~~

Source-level ``u`` performs sequential probability-proportional-to-remaining-
weight draws by resulting value.  After selecting a value, that value and its
entire combined weight are removed, the remaining total is recomputed, and the
next ordered draw occurs.  The requested count cannot exceed the number of
distinct positive-weight values.

Order is part of a RollSet outcome.  For weights ``A=2, B=1, C=1`` and two
unique draws, ``[A, B]`` has probability ``1/4`` while ``[B, A]`` has
probability ``1/6``.  Sorting or grouping may later merge ordered outcomes only
according to its ordinary typed semantics.

Postfix option ``u`` remains deterministic deduplication after with-replacement
sampling.  It does not refill and is analyzed as an ordinary transformation,
not as source-level sampling without replacement.

Transformations and control flow
--------------------------------

The provisional v2.1 boundary is conservative:

Supported
   Literal typed values, deterministic variables, finite numeric/range/list
   dice, checked ``+``, ``-``, and ``*``, pure validators, and deterministic
   keep, drop, filter, sort, count, occurrences, unique, paint, split, and group
   transformations are exact when the global limits hold.

Bounded pending prototype evidence
   Integer division with a statically non-zero outcome set, exponentiation with
   finite non-negative exponents, source-level unique draws, one-time reroll,
   merge with another exact expression, literal-count repeat, and conditionals
   whose predicate and every reachable branch are exact.  Issue 32 must measure
   state growth and issue 33 must accept or reject each before RFC acceptance.

Unsupported in v2.1
   Multiple Program instructions, bind/history dependence, backward jump,
   dynamic or probabilistic variables, and unbounded source-generating options:
   explode, keep-and-explode, reroll-until, and reroll-and-add.  Their runtime
   distributions interact with finite budgets or have unbounded support; an
   unbudgeted mathematical distribution would not be the same operation as the
   bounded Engine.

The complete checked matrix is normative for identifiers and provisional
status:

.. literalinclude:: ../rfcs/0006-capability-matrix.json
   :language: json
   :caption: docs/rfcs/0006-capability-matrix.json

Exact distributions
-------------------

The normative examples cover uniform numeric convolution, deterministic keep,
integer-weighted list selection, and ordered weighted draws without
replacement.  Probabilities use decimal-string rational components and typed,
self-contained ``AnalysisValue`` objects:

.. literalinclude:: ../rfcs/0006-distributions.json
   :language: json
   :caption: docs/rfcs/0006-distributions.json

Issue 32 must cross-check these tables with exhaustive enumeration and extend
them with every construct proposed as supported or bounded.  The prototype
records states visited, peak states, support size, rational bit width, bytes,
and elapsed time; elapsed time informs defaults but is never a semantic limit.

Complexity and resource policy
------------------------------

Exact analysis adds counters to RFC-0002 rather than bypassing it:

``analysis_states``
   Number of materialized input and intermediate states before equal-value
   merging.  Default 100,000; hard maximum 10,000,000.

``analysis_support``
   Maximum distinct final AnalysisValues.  Default 100,000; hard maximum
   1,000,000.

``analysis_operations``
   Rational additions, multiplications, comparisons, and typed transformations.
   Default 1,000,000; hard maximum 100,000,000.

``analysis_bytes``
   Estimated owned state, keys, numerators, denominators, and output.  Default
   64 MiB; hard maximum 512 MiB.

``analysis_rational_bits``
   Maximum bit length of any reduced numerator or denominator.  Default 4,096;
   hard maximum 65,536.

Charges are monotonic and checked before allocation or arithmetic.  Ordinary
source bytes, parse depth, AST nodes, collection, work, output, deadline, and
cancellation limits also apply.  A caller may lower limits but cannot exceed
hard maxima.  No partial distribution survives a failure.

Default values remain provisional until issue 32 publishes measurements on the
supported matrix.  Changing a default before RFC acceptance updates the
machine contract and examples.  Changing a hard maximum or counter meaning
after acceptance requires an RFC amendment.

Stable errors
-------------

Analysis failures use the RFC-0003 error envelope with phase ``analysis`` and a
source span when a construct owns one.  The v2.1 registry includes:

``analysis.unsupported_construct``
   The construct is outside the exact capability matrix.  Fields include
   ``construct``, ``capability_status``, and ``reason``.

``analysis.unsupported.program_arity``
   Exact analysis received anything other than one Instruction.

``analysis.possible_runtime_error``
   At least one reachable outcome can fail ordinary evaluation.  Fields include
   the ordinary error code and triggering span.

The limit errors ``analysis.state_limit``, ``analysis.support_limit``,
``analysis.operation_limit``, ``analysis.byte_limit``, and
``analysis.rational_limit`` mean that one named exact-analysis counter would
exceed its accepted limit.  Fields include ``limit``, ``consumed``, and
``requested``.

The cancellation errors ``analysis.cancelled`` and
``analysis.deadline_exceeded`` mean that the shared cancellation or deadline
boundary fired between monotonic work units.  These retain RFC-0004 exception
inheritance.

Sampling continues to use ordinary parse, validation, evaluation, random,
budget, cancellation, and serialization codes.  It does not relabel an Engine
failure as a statistical error.

Serialization and versioning
----------------------------

``analysis_schema_version`` starts at ``1.0`` and is independent of the package
and RFC-0003 result-schema versions.  ``AnalysisValue`` reuses the RFC-0003
scalar, text, Boolean, and nested Values shapes.  Its RollSet is deliberately
materialized as ordered scalar or text items plus deterministic annotations;
it never contains RollReferences, RollNodes, source nodes, or execution traces,
because no concrete random draw occurred.  An ``analysis_plan`` records source
spans, construct IDs, state counts, limits, and transformations for auditability
without pretending it is a roll trace.

Sampling embeds ordinary RFC-0003 ProgramResults only when requested.  Its
histogram normalizes top-level Values into ``AnalysisValue`` so equal RollSets
from separate executions aggregate independently of node identity.  The compact
summary names the result schema, analysis schema, random protocol, batch
protocol, and aggregation version used.

Unknown analysis schema, aggregation, quantile, or confidence versions fail
explicitly.  Consumers never guess a version from fields.

CLI and TUI boundary
--------------------

Issue 36 exposes different commands and controls for sampling and exact mode.
The CLI uses explicit subcommands or flags, prints the active mode and limits,
and exports stable JSON/CSV.  Exact errors display the capability reason and
never prompt to fall back automatically.  A user may make a separate explicit
sampling request afterward.

Long operations run outside the TUI event loop, report deterministic progress
counters where available, and share the Engine cancellation token.  Closing a
view cancels work and waits for termination; it cannot detach a hidden analysis
that continues consuming resources.

Cross-RFC dependencies
----------------------

RFC-0001 owns accepted syntax, typed option effects, weight normalization,
canonical text, and the distinction between source-level and postfix unique.
RFC-0002 owns random words, seeds, budgets, cancellation, atomic failure, and
checked arithmetic.  RFC-0003 owns Value and error serialization.  RFC-0004
owns immutable Engine lifecycle, detached Rust execution, batch seeds, typed
Python objects, and exception inheritance.  RFC-0005 owns conformance case
lifecycle, release evidence, supported wheel claims, and publication approval.

RFC-0006 may narrow exact support but may not change ordinary execution to make
analysis easier.  Sampling and exact implementation issues must add RFC-0005
cases without inventing analysis-only language semantics.

Implementation sequence
-----------------------

#. Issue 3 lands this draft, checked artifacts, and provisional boundaries.
#. Issue 32 prototypes the exact state engine, verifies normative
   distributions, and measures every bounded construct and proposed limit.
#. Issue 33 accepts the final capability matrix and updates this RFC from Draft
   to Review/Accepted through human review.
#. Issues 18 and 22 finish public seeds, deterministic batch envelopes,
   cancellation, and detached execution required by sampling.
#. Issue 31 implements ``Engine.sample`` and the checked aggregation contract in
   Rust with installed-Python parity and benchmarks.
#. Issue 36 exposes explicit cancellable sampling and exact workflows in CLI and
   TUI clients.

Rejected alternatives
---------------------

One ``analyze(..., exact=True)`` method
   A mode flag creates a result union and makes logs and callers vulnerable to
   accidental fallback.  Separate methods and result classes make intent
   structural.

Automatically sample when exact analysis is too large
   The result would no longer satisfy the caller's request and could be mistaken
   for proof.  ``analysis.*_limit`` is the only valid response.

Floating-point exact probabilities
   Rounding can make equal paths differ and totals fail to equal one.  Reduced
   arbitrary-precision rationals preserve the finite semantics.

Return per-instruction marginals for Programs
   Marginals discard correlations and become wrong when bind, branches, or
   shared history affect later instructions.  V2.1 exact mode accepts one
   Instruction.

Analyze unbounded generation without runtime budgets
   It would describe a different mathematical process from the bounded Engine
   and hide non-zero resource-error probability.

Truncate small probabilities
   Truncation is approximation even if the removed mass is displayed.  It
   belongs in a future explicitly approximate method, not exact analysis.

Use display strings as outcome keys
   Formatting is locale-dependent and can merge distinct typed Values.
   Canonical ``AnalysisValue`` JSON is the key.

Acceptance gate
---------------

RFC-0006 may move from Draft to Review when:

* the checked API contract, matrix, and rational distributions pass the quality
  gate;
* issue 32 reproduces every normative table by exhaustive enumeration and
  publishes state/memory measurements for each bounded construct;
* proposed default and hard limits are supported by those measurements; and
* RFC-0001 through RFC-0005 contain no conflicting weight, Value, random,
  budget, batch, error, documentation, or release meaning.

It may move from Review to Accepted only when:

* issue 33 classifies every matrix entry with no provisional status;
* issues 31, 32, 33, and 36 reference the final API, errors, and capability
  identifiers; and
* a human review accepts the one-Instruction exact boundary, weighted unique
  semantics, sampling statistics, complexity ceilings, and no-fallback rule.

Implementation completion is not required for RFC acceptance.  M6 completion
requires the accepted contract, executable exact and sampling conformance,
public clients, and the ``v2.1.0`` release evidence from RFC-0005.

References
----------

* `num BigRational documentation
  <https://docs.rs/num/latest/num/type.BigRational.html>`_
* `Hyndman and Fan, Sample Quantiles in Statistical Packages
  <https://robjhyndman.com/publications/quantiles/>`_
* `Efraimidis, Weighted Random Sampling over Data Streams
  <https://arxiv.org/abs/1012.0256>`_
* :ref:`rfc-0001`
* :ref:`rfc-0002`
* :ref:`rfc-0003`
* :ref:`rfc-0004`
* :ref:`rfc-0005`
