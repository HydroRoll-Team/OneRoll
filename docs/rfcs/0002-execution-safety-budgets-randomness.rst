.. _rfc-0002:

RFC-0002: Execution Safety, Budgets, and Randomness
===================================================

:Status: Accepted
:Target: OneRoll 2.0
:Discussion: https://github.com/HydroRoll-Team/OneRoll/issues/6
:Last updated: 2026-07-29

Summary
-------

Every OneRoll evaluation runs inside one request-scoped ``ExecutionContext``.
The context owns the random stream, immutable variables, resource counters,
cancellation state, and trace builder for the complete Program.  Public helper
functions, the Rust Engine, Python, CLI, and TUI must all delegate to this same
execution path.

This RFC freezes three safety properties before the v2 implementation expands:

* structural and dynamic work has explicit default limits and hard ceilings;
* seeded evaluation uses a versioned, portable random protocol with unbiased
  bounded sampling; and
* any limit, cancellation, entropy, or arithmetic failure atomically returns a
  structured error instead of a partial Program result.

Context
-------

The v1 compatibility engine has two useful but incomplete protections: a
10,000 generated-face limit and a 1,000 top-level instruction limit.  It still
uses ``random::<u32>() % sides``, which introduces modulo bias, and each Python
entry point constructs an independent calculator.  There is no stable seed,
parse-depth limit, AST-node limit, collection/output limit, cancellation
contract, or machine-readable budget error.

The v2 language adds weighted lists, validators, option pipelines, repeat,
conditionals, batches, and traces.  Counting only retained dice faces would let
discarded values, pure-scalar Programs, nested functions, or expanding
collections bypass the safety boundary.  The complete request therefore needs
one shared policy and one shared set of counters.

Goals
-----

* Make every public execution entry point safe for untrusted input by default.
* Make resource use monotonic across all instructions, branches, functions,
  batches, rerolls, explosions, and renderable outputs in one request.
* Reproduce seeded results across Rust, Python, CLI, supported architectures,
  and compatible OneRoll releases.
* Remove modulo bias from numeric and weighted-list sampling.
* Define stable, spanned errors for policy, budget, entropy, deadline, and
  cancellation failures.
* Keep an Engine reusable and safe for concurrent calls after success or error.

Non-goals
---------

* Reserving memory or CPU with operating-system-level isolation.  Services may
  add process, container, or platform quotas around the Engine.
* Treating a wall-clock deadline as a deterministic semantic budget.
  Structural counters remain the hard termination guarantee.
* Providing cryptographic key generation or a security-sensitive random API.
* Returning partial Program results in v2.0.
* Freezing exact probability-analysis limits; RFC-0006 owns that capability.

Execution architecture
----------------------

``Engine`` is immutable after construction and contains accepted configuration,
not mutable request state.  Conceptually, execution has these inputs:

.. code-block:: text

   EngineConfig {
       resource_policy,
       random_policy,
       compatibility_mode,
   }

   ExecutionRequest {
       source,
       variables,
       seed?,
       cancellation?,
       deadline?,
   }

Each call to ``Engine.roll``, ``Engine.run``, or a bounded batch operation
creates exactly one internal context:

.. code-block:: text

   ExecutionContext {
       accepted_policy,
       remaining_budget,
       rng,
       effective_seed,
       variables,
       cancellation,
       deadline,
       trace_builder,
   }

Convenience functions construct or reuse a default immutable Engine and still
create a fresh context per call.  They must not contain a second parser or
evaluator.  One ``run`` call uses one context for every instruction.  Repeat,
conditions, batches, and future functions receive a child scope referencing the
same counters and RNG rather than constructing a new context.

Lifecycle invariants
~~~~~~~~~~~~~~~~~~~~

* Source and host-environment limits are checked before parsing or allocation.
* Parsing and validation complete before the first random word whenever a
  failure can be detected without evaluation.
* Budget counters only increase.  A nested scope cannot refund, replace, or
  reset a request counter.
* Charges are checked with overflow-safe arithmetic before the associated work
  or allocation begins.
* An Engine stores no random cursor, partial trace, or variable mutation between
  requests.
* Concurrent requests never share an ``ExecutionContext``.

Resource policy
---------------

Every structural resource has a safe default and a process-level hard ceiling.
An Engine configuration may choose a value from zero through the hard ceiling.
The convenience API uses the default column.  A configuration above a hard
ceiling is rejected before execution with
``policy.limit_above_hard_max``.  No Python, CLI, or ordinary Rust option
disables a structural ceiling.

The initial v2.0 matrix is normative:

.. list-table:: Resource matrix
   :header-rows: 1
   :widths: 19 34 13 15 19

   * - Resource
     - Unit and charging point
     - Default
     - Hard maximum
     - Exhaustion code
   * - ``source_bytes``
     - UTF-8 bytes in the complete Program, before parsing
     - 65,536
     - 1,048,576
     - ``limit.source_bytes``
   * - ``environment_items``
     - Named plus positional host variables, before validation
     - 1,024
     - 16,384
     - ``limit.environment_items``
   * - ``environment_bytes``
     - UTF-8 and serialized value bytes supplied by the host
     - 1,048,576
     - 16,777,216
     - ``limit.environment_bytes``
   * - ``parse_depth``
     - Nested parentheses, lists, validators, calls, and blocks
     - 64
     - 256
     - ``limit.parse_depth``
   * - ``ast_nodes``
     - Every typed Program, Instruction, expression, option, and validator node
     - 4,096
     - 65,536
     - ``limit.ast_nodes``
   * - ``parsed_instructions``
     - Every top-level or nested Instruction present in source
     - 1,000
     - 10,000
     - ``limit.parsed_instructions``
   * - ``executed_instructions``
     - Every Instruction activation, including repeats and branches
     - 10,000
     - 1,000,000
     - ``limit.executed_instructions``
   * - ``nesting_depth``
     - Active expression, function, repeat, or conditional evaluation scopes
     - 32
     - 128
     - ``limit.nesting_depth``
   * - ``source_items``
     - Requested dice count or declared range/list source cardinality
     - 10,000
     - 100,000
     - ``limit.source_items``
   * - ``generated_values``
     - Every semantic draw, including discarded, rerolled, and exploded values
     - 10,000
     - 1,000,000
     - ``limit.generated_values``
   * - ``rng_words``
     - Every raw 64-bit RNG word, including rejection-sampling retries
     - 20,000
     - 2,000,000
     - ``limit.rng_words``
   * - ``collection_items``
     - Maximum cardinality of any live Values or RollSet collection
     - 10,000
     - 100,000
     - ``limit.collection_items``
   * - ``trace_nodes``
     - Every source, transform, branch, retained, and discarded trace node
     - 20,000
     - 200,000
     - ``limit.trace_nodes``
   * - ``output_items``
     - Final externally visible values, results, and trace roots
     - 10,000
     - 100,000
     - ``limit.output_items``
   * - ``output_bytes``
     - UTF-8 bytes in the stable serialized result before client decoration
     - 8,388,608
     - 67,108,864
     - ``limit.output_bytes``
   * - ``work_units``
     - AST, predicate, option, collection-item, and function-loop work
     - 1,000,000
     - 50,000,000
     - ``limit.work_units``
   * - ``batch_samples``
     - Requested executions in one batch or statistical sampling call
     - 10,000
     - 1,000,000
     - ``limit.batch_samples``

The hard ceilings are compatibility commitments for OneRoll 2.x, not claims
that every maximum-sized request is inexpensive.  Lower defaults are allowed in
patch releases when required to fix a denial-of-service risk.  Raising a hard
ceiling or changing a charge unit requires an RFC amendment and conformance
update.

Charging rules
~~~~~~~~~~~~~~

The implementation must centralize charging on the context.  A subsystem asks
to charge ``n`` units and receives either success or one structured error with
``resource``, ``used``, ``requested``, and ``limit`` fields.  Saturating or
wrapping a counter is forbidden.

``work_units`` closes gaps between specific counters.  At minimum, one unit is
charged for each AST node evaluation, predicate evaluation, option application
per input item, collection item scanned or copied, executed instruction, and
function-loop iteration.  A more specialized counter does not replace the work
charge: generating one die charges an RNG word, one generated value, applicable
trace/output work, and ordinary work units.

The engine pre-charges known cardinality before allocation.  When cardinality is
data-dependent, it charges incrementally before appending each item.  Selection
or filtering does not refund values, RNG words, work, or trace nodes already
consumed.  Splitting equivalent work across semicolons, branches, nested calls,
or convenience functions inside one request cannot change the available
budget.

Random protocol
---------------

Algorithm identity
~~~~~~~~~~~~~~~~~~

The v2.0 random protocol identifier is ``oneroll-chacha12-v1``.  It uses a
ChaCha generator with 12 rounds, a 256-bit seed, a zero stream identifier, and
the raw 64-bit word order defined by ``ChaCha12Rng``.  The implementation may
use ``rand_chacha`` but must retain reference-vector tests across dependency
upgrades.

``StdRng`` is explicitly rejected for replay because its documentation marks it
non-portable and permits future algorithm replacement.  The selected ChaCha
implementation is deterministic and portable and publishes reference vectors.
Changing rounds, seed expansion, stream identifier, raw-word order, bounded
sampling, or construct traversal requires a new protocol identifier.  Existing
identifiers remain readable for replay throughout the 2.x support window.

Seed contract
~~~~~~~~~~~~~

The canonical seed is exactly 32 bytes and is rendered as 64 lowercase
hexadecimal digits in result metadata.

* A Rust 32-byte seed is used unchanged.
* A Python or CLI unsigned 64-bit integer is encoded little-endian into bytes
  0 through 7; bytes 8 through 31 are zero.
* A hexadecimal seed must contain exactly 64 hexadecimal digits, with an
  optional ``0x`` prefix.
* Negative, oversized, short, or malformed seeds fail with
  ``random.invalid_seed`` before parsing begins.
* When no seed is supplied, the engine obtains all 32 bytes from the operating
  system random source.  Entropy failure returns ``random.entropy_unavailable``
  and never falls back to time, process identifiers, or a constant.

Every successful result records ``algorithm`` and the effective canonical
seed.  An evaluation error after random work begins records the same replay
descriptor and the number of consumed RNG words, but no partial values.  The
seed describes replayability, not cryptographic secrecy.

Unbiased bounded integers
~~~~~~~~~~~~~~~~~~~~~~~~~

Numeric dice, range dice, weighted-list selection, and without-replacement
indices use one normative ``uniform_below(bound)`` primitive.  ``bound`` must
be positive.  Arithmetic uses a type able to represent ``2**64``:

.. code-block:: text

   zone = floor(2**64 / bound) * bound
   loop:
       charge rng_words by 1
       x = rng.next_u64()
       if x < zone:
           return x % bound

This is rejection sampling: the accepted domain contains an equal number of
representatives for every output.  The rejected tail is never mapped with
modulo.  A semantic value is charged only after an index is accepted; each raw
attempt remains charged as an RNG word.

A numeric inclusive range first computes its width with checked arithmetic and
then adds ``uniform_below(width)`` to its lower bound.  A weighted list uses
checked unsigned integer weights, draws below their positive total, and selects
the first item whose cumulative input-order weight exceeds the draw.  Floating
point sampling is forbidden.

Random consumption order
~~~~~~~~~~~~~~~~~~~~~~~~

Programs consume randomness in source order: instructions from left to right,
expression operands in canonical evaluation order, source values in ascending
draw index, and option-generated values in left-to-right pipeline order.
Discarded values still occupy their original position in the stream.  Parallel
batch execution must derive an independent sub-seed from the request seed and
stable sample index; it may not race on a shared generator.  The exact sub-seed
derivation is frozen with the batch API in RFC-0004 before parallel batches
ship.

Reference vectors
~~~~~~~~~~~~~~~~~

For the all-zero 256-bit seed under ``oneroll-chacha12-v1``, the first four raw
words are:

.. code-block:: text

   53f955076a9af49b
   d583265f12ce1f81
   1474e049bbc32904
   5f15ae2ea589007e

Using the normative bounded sampler, the first four independent d6 values are
``[4, 4, 3, 3]`` and d20 values are ``[4, 2, 1, 15]``.  A fresh request with the
same seed selecting from ``["common"[80%], "rare"[20%]]`` returns ``"common"``.
Rust and installed Python conformance tests must assert these vectors before a
random dependency upgrade can merge.

Cancellation and deadlines
--------------------------

Structural budgets guarantee termination even when a caller never provides a
cancellation token.  Cancellation and deadlines provide responsiveness on top
of those budgets.

The core Rust and Python Engine has no default wall-clock deadline.  A mandatory
semantic timeout would make the same source, seed, and policy succeed or fail
according to machine speed and system load.  The reference CLI and TUI apply a
5,000 millisecond client deadline.  Hosted services must set a deployment
deadline; 5,000 milliseconds is the recommended default and 60,000 milliseconds
is the recommended deployment maximum.  These client and deployment values are
operational policy, not part of deterministic language semantics and not a
replacement for structural hard ceilings.

The optional cancellation token is thread-safe and monotonic: it changes from
active to cancelled at most once.  The context checks it before every budget
charge, RNG word, potentially growing allocation, and instruction boundary.
The monotonic deadline is checked at request start, at instruction and
allocation boundaries, and at least every 256 work units.  System wall-clock
changes cannot extend it.

Cancellation returns ``execution.cancelled``.  Deadline exhaustion returns
``execution.deadline_exceeded``.  If both are visible at one checkpoint,
explicit cancellation wins.  Neither condition may be converted to an empty or
truncated success.  Cancellation latency is bounded in work checkpoints, not in
wall-clock milliseconds; service operators still need outer process timeouts.

Atomic failure and error contract
---------------------------------

One Program is the atomic result boundary.  Parse, validation, budget,
arithmetic, entropy, cancellation, or deadline failure returns no
``ProgramResult``, no instruction prefix, and no partial trace.  Request-local
variables, RNG state, counters, and trace nodes are discarded.  The immutable
Engine remains reusable.

Safety failures use the structured error vocabulary shared with RFC-0003.  The
minimum machine-readable fields are:

.. code-block:: text

   ExecutionError {
       phase: parse | validate | evaluate | cancel,
       code: stable_ascii_identifier,
       message: human_readable_text,
       span?: { start_byte, end_byte },
       resource?: resource_name,
       used?: integer,
       requested?: integer,
       limit?: integer,
       random?: { algorithm, seed, rng_words },
   }

Clients branch on ``code``, never localized ``message`` text.  A resource error
uses the code in the normative matrix.  Configuration errors use
``policy.limit_above_hard_max`` or ``policy.invalid_limit``.  Random setup uses
``random.invalid_seed`` or ``random.entropy_unavailable``.  Checked arithmetic
uses ``arithmetic.overflow``, ``arithmetic.divide_by_zero``, and
``arithmetic.invalid_exponent``.  RFC-0003 owns the final serialized envelope,
exception classes, and trace schema without changing these meanings.

Thread safety and language bindings
-----------------------------------

An immutable configured Engine must be safe to share across threads.  Each call
owns its context and deterministic generator.  Two concurrent calls using the
same configuration, source, variables, and seed produce identical results
independently; scheduling cannot change draw order.

Python does not use ``random.Random`` and the CLI does not seed separately.
Both pass seed and policy data to the Rust Engine.  CPU-bound parsing and
evaluation should release the GIL once Python-owned inputs have been converted,
while cancellation remains callable from another thread.  Python exceptions
expose the same structured fields as Rust errors.

The CLI accepts a decimal unsigned 64-bit seed or canonical hexadecimal seed
and prints the effective seed in machine-readable output.  Human output may
hide it by default but must expose it through an explicit replay/details flag.
TUI work runs outside the event loop and uses the same cancellation token.

Verification contract
---------------------

The implementation issues unblocked by this RFC must add the following shared
evidence to Rust and the installed Python package:

Boundary tests
   Exercise zero, immediately below, exactly at, and one above every default and
   configurable limit.  Nested and semicolon-separated forms must prove that a
   counter cannot reset.

Adversarial termination tests
   Cover infinite explosions, impossible reroll-until predicates, deeply nested
   parentheses/functions/blocks, enormous pure-scalar Programs, expanding
   repeats, option pipelines, output-heavy traces, and cancellation during each
   dynamic construct.

Determinism tests
   Assert the reference vectors, identical Rust/Python results, repeatable
   errors at the same RNG word, and independence from thread scheduling.

Bias tests
   Test ``uniform_below`` exhaustively with a reduced-width fake RNG for bounds
   1 through 16 so every accepted output has equal preimages and rejected tails
   are retried.  Run fixed-seed distribution smoke tests for d2, d3, d6, d20,
   numeric ranges, weighted lists, and unique draws.  Statistical smoke tests
   use predeclared sample counts and thresholds and run in scheduled CI; the
   exhaustive algorithmic test remains the non-flaky merge gate.

Property and fuzz tests
   Assert no panic, hang, wraparound, out-of-range face, budget increase, hidden
   partial success, or post-cancellation mutation.  Every discovered failure is
   retained as a regression seed.

Implementation sequence
-----------------------

This RFC unlocks vertical implementation issues rather than landing all changes
in one patch:

#. Issue 13 introduces ``ResourcePolicy``, request-scoped counters, defaults,
   hard ceilings, and shared entry-point enforcement.
#. Issue 18 introduces ``oneroll-chacha12-v1``, seed metadata, and the unbiased
   bounded sampler.
#. Issue 17 moves totals and intermediate arithmetic to checked ``i64``.
#. Issue 12 exposes the stable structured error and span contract with RFC-0003.
#. Issue 23 adds the permanent fuzz and property gates after those primitives
   exist.

Later dice, validator, option, function, batch, CLI, and TUI issues must charge
the existing context instead of creating feature-specific limits or random
sources.

Rejected alternatives
---------------------

``rand::random`` or ``ThreadRng`` per face
   Neither exposes a replayable request stream, and modulo mapping is biased.

``StdRng`` with an integer seed
   The Rust Rand documentation explicitly marks ``StdRng`` non-portable and
   permits algorithm replacement.  Its name is not a replay protocol.

Modulo mapping without rejection
   Unless the bound divides ``2**64``, some outcomes receive more raw inputs
   than others.

One generated-face counter only
   It does not bound parsing, pure scalar work, validators, collections,
   functions, output, or discarded trace nodes.

Reset budgets per instruction or helper call
   Attackers could split equivalent work across semicolons, repeats, or public
   convenience functions.

Return completed instruction prefixes on error
   This creates partial hidden state and makes retry, replay, and client logic
   ambiguous.  V2.0 keeps the Program result atomic.

Wall-clock timeout as the only limit
   Timing depends on hardware and load and cannot provide deterministic
   conformance or memory bounds.

References
----------

* `rand StdRng portability contract
  <https://docs.rs/rand/0.9.2/rand/rngs/struct.StdRng.html>`_
* `rand_chacha deterministic portable generators
  <https://docs.rs/rand_chacha/0.9.0/rand_chacha/>`_
* `rand OsRng operating-system entropy contract
  <https://docs.rs/rand/0.9.2/rand/rngs/struct.OsRng.html>`_
* :ref:`rfc-0001`
