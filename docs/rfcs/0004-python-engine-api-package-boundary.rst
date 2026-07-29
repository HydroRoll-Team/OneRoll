.. _rfc-0004:

RFC-0004: Python Engine API and Package Boundary
================================================

:Status: Review
:Target: OneRoll 2.0
:Discussion: https://github.com/HydroRoll-Team/OneRoll/issues/5
:Last updated: 2026-07-29

Summary
-------

OneRoll 2.0 exposes one immutable, shareable ``Engine`` as the primary Python
API.  Every parse, validation, evaluation, and batch call crosses the Python/
Rust boundary once for its CPU work, creates a fresh request context, and
returns immutable Rust-backed Python objects matching RFC-0003.  Compatibility
helpers remain adapters over that Engine throughout 2.x.

The core wheel has no Rich or Textual dependency.  Human CLI and TUI features
are optional extras and use a thin standard-library entry point.  This keeps
``import oneroll`` suitable for libraries, services, notebooks, worker pools,
and minimal containers.

Current baseline
----------------

The 1.x package currently exports a Python ``OneRoll`` wrapper and dictionary
helpers over a PyO3 ``_core`` extension.  It does not yet expose ``Engine``,
typed results, structured exception classes, host variables, stable seeds,
cancellation, or the RFC-0003 batch envelope.  CPU-bound binding methods also
execute while attached to the Python interpreter, and Rich and Textual are
required dependencies even when only the core extension is used.

This RFC is a target contract, not a claim that those surfaces already exist.
Its checked stub and manifest prevent implementation issues from inventing
incompatible signatures independently.

Goals
-----

* Freeze one Python API over the RFC-0001 language, RFC-0002 request model, and
  RFC-0003 typed result/error boundary.
* Make Engine instances safe to reuse concurrently without request-state
  leakage or scheduling-dependent randomness.
* Release the GIL around Rust-only CPU work while keeping cancellation callable
  from another Python thread.
* Define deterministic, bounded, atomic batch execution before parallelism.
* Keep the core install free of presentation dependencies.
* Provide an explicit 1.x-to-2.x migration and deprecation window.

Non-goals
---------

* Exposing parser AST nodes as a stable public API.
* Accepting a parsed object as executable input and bypassing request charges.
* Adding Python callbacks or progress hooks inside detached Rust execution.
* Parallelizing samples inside ``run_batch`` in 2.0.
* Promising free-threaded CPython wheels before the binding dependency and
  concurrency suite support them.
* Removing the v1 dictionary adapters in 2.0.

Primary Engine surface
----------------------

The normative signatures are in ``0004-target-api.pyi``.  The primary surface
is:

.. code-block:: python

   engine = oneroll.Engine(
       resource_policy=oneroll.ResourcePolicy(),
       compatibility_mode="strict_v2",
   )

   parsed = engine.parse(source)
   validated = engine.validate(source, variables=variables)
   instruction = engine.roll(expression, variables=variables, seed=seed)
   program = engine.run(source, variables=variables, seed=seed)
   batch = engine.run_batch(source, 100, variables=variables, seed=seed)

The constructor arguments are keyword-only.  ``resource_policy=None`` selects
RFC-0002 safe defaults and ``compatibility_mode`` defaults to ``strict_v2``.
An Engine stores only accepted immutable configuration.  It never stores host
variables, an effective seed, an RNG cursor, counters, a deadline, or a
cancellation token.

Each method creates one new RFC-0002 ``ExecutionContext``.  The Rust Engine is
``Send + Sync`` and the Python class is frozen.  Concurrent calls on one Engine
are independent: equal source, variables, seed, and policy produce equal
results regardless of scheduling.

Parse and validation boundaries
-------------------------------

``parse(source)`` performs source charging and syntax construction only.  It
returns immutable ``ParsedProgram`` introspection data and never initializes
randomness.  ``validate(source, variables=...)`` additionally resolves names,
types, cardinalities, compatibility rules, and static policy checks, then
returns immutable ``ValidatedProgram`` introspection data.  It also never
initializes randomness and does not retain caller-owned variable values.

Parsed and validated objects are not accepted by ``roll``, ``run``, or
``run_batch``.  Evaluation always accepts source text so a caller cannot reuse
an object to bypass per-request source, parse, AST, environment, or output
charges.  A future compiled-program API requires its own cache-accounting and
compatibility RFC.

``roll`` accepts exactly one Instruction and returns its
``InstructionResult``.  A separator or second instruction fails validation.
``run`` accepts a complete Program and returns ``ProgramResult``.  Neither
method contains a Python-side parser or evaluator.

Request inputs
--------------

``variables`` is copied and converted before Rust execution begins.  A key is
either a QML-compatible identifier string or a non-negative integer.  A value
is a signed 64-bit integer, string, Boolean, or recursively nested finite
sequence of those values.  Boolean conversion is checked before integer
conversion.  Floats, bytes, mappings as values, custom objects, mutable views,
and host-created RollSets are rejected with structured validation errors.

The copied environment is immutable for the request.  Caller mutation after a
method starts cannot affect validation or evaluation.  RFC-0002 environment
item and byte limits are charged before retaining the converted values.

``seed`` accepts a Python integer in the unsigned 64-bit range or exactly 64
hexadecimal digits.  Integer expansion, hexadecimal normalization, entropy,
and replay metadata follow RFC-0002.  Python's ``random`` module is never part
of the execution path.

Cancellation and timeout
------------------------

``CancellationToken`` is thread-safe and one-shot.  ``cancel()`` changes it
from active to cancelled at most once; ``cancelled`` is a read-only Boolean.
The token contains no reference to an Engine or Python callback.

``timeout`` is an optional finite positive number of relative seconds.  The
binding converts it once to a monotonic Rust deadline before detaching.  Zero,
negative, NaN, and infinite values fail validation.  The core Engine has no
default timeout; the reference CLI and TUI apply the RFC-0002 five-second
client policy.

Typed objects and serialization
-------------------------------

Engine methods return frozen Rust-backed classes.  Sequences are tuples and
maps are read-only views, so result data cannot be mutated across consumers or
threads.  Every public result, value, diagnostic, and descriptor exposes
read-only attributes and ``to_dict()``.  ``to_dict()`` returns a detached deep
copy conforming to the RFC-0003 schema; mutating that dictionary never mutates
the original object.

``ParsedProgram`` and ``ValidatedProgram`` are also frozen, but are
introspection objects rather than RFC-0003 result envelopes.  Their serialized
shape is informational and is not accepted as evaluation input.

Exception hierarchy
-------------------

Python exceptions retain RFC-0003's fields and codes:

.. code-block:: text

   OneRollError(ValueError)
   +-- ParseError
   +-- ValidationError
   +-- EvaluationError
   |   +-- ResourceLimitError
   |   +-- RandomError
   |   +-- ArithmeticEvaluationError
   +-- CancellationError
       +-- DeadlineExceededError

``OneRollError`` subclasses ``ValueError`` so existing broad handlers continue
to catch invalid input during the 2.x migration.  Its attributes expose
``phase``, ``code``, ``span``, resource counters, random metadata,
``expected``, and ``replacement`` as applicable.  ``to_dict()`` returns the
inner RFC-0003 error object, not the outer error envelope.

The subclass is selected by stable meaning, while ``code`` remains the
programmatic compatibility key.  Adding a narrower subclass does not change a
code or field.  Explicit cancellation maps to ``CancellationError`` and an
expired deadline maps to ``DeadlineExceededError``.

GIL and thread-safety contract
------------------------------

The binding follows a three-stage boundary:

#. While attached to Python, validate scalar arguments and copy source,
   variables, seed, policy, token handle, and timeout into Rust-owned values.
#. Release the GIL with the supported PyO3 equivalent of ``allow_threads`` for
   all parser, validator, evaluator, serializer-charge, and batch CPU work.
#. Reacquire it only to create immutable result objects or raise the structured
   exception.

The detached closure must not retain or access ``PyObject``, invoke Python,
format through Rich, or call a user callback.  Another Python thread can call
``CancellationToken.cancel()`` while evaluation is detached.  CLI and TUI
progress is client-side polling of worker completion and token state; it is not
a core callback protocol.

The repository currently uses PyO3 0.19.  Free-threaded CPython wheels must not
be advertised or published until PyO3 is upgraded to a release with explicit
free-threaded support (at least 0.23), all exposed classes satisfy that model,
and the concurrency suite passes on a free-threaded interpreter.  Ordinary GIL
release on supported CPython versions is an earlier, independent requirement.

Batch contract
--------------

``run_batch(program, samples, ...)`` requires a positive sample count.  It
crosses into Rust once, parses and validates once, and evaluates samples in
increasing index order.  One request policy, cancellation token, timeout, and
set of counters applies to the complete batch.  No ``workers`` parameter,
progress callback, or per-sample Python crossing exists in 2.0.

A root seed is accepted or generated once.  Sample ``i`` receives:

.. code-block:: text

   SHA-256(
       b"OneRoll batch seed v1\0"
       || root_seed_32_bytes
       || uint64_le(i)
   )

The protocol identifier is ``oneroll-sha256-batch-v1``.  For an all-zero root
seed, the first two derived seeds are:

.. code-block:: text

   1f6bac00ab7392f2573c212d426bae43bd25654c58c2473a7b264d7d085dfa8d
   8edeea3ef906166ba806febfe5db1936e623009947ef040e0ef5cfd860465b2c

The sequential rule is normative for 2.0 and makes profiling and failure order
unambiguous.  Independent Engine calls may execute concurrently.  A future
internally parallel batch implementation may ship only if it preserves exact
sample order, sub-seeds, shared budget semantics, failure selection, and wire
output.

``BatchResult`` retains the root seed and ordered ``ProgramResult`` children.
The complete batch is atomic.  A failure returns only the RFC-0003 error with
batch root context and the failing sample index; previously completed children
are discarded.

Package and entry-point boundary
--------------------------------

OneRoll 2.0 declares no required Python dependencies for its core wheel:

.. code-block:: toml

   dependencies = []

   [project.optional-dependencies]
   cli = ["rich>=14.1.0"]
   tui = ["rich>=14.1.0", "textual>=6.1.0"]

``pip install oneroll`` provides ``import oneroll`` and the Engine without
importing Rich or Textual.  ``pip install oneroll[cli]`` provides rich human
CLI rendering; ``pip install oneroll[tui]`` provides both CLI and Textual TUI
support.  This follows the PyPA optional-dependency model.  Entry-point extras
are not encoded in script declarations because that mechanism is discouraged
for new publishing metadata.

The ``oneroll`` and ``1roll`` scripts remain installed for compatibility and
point to a thin standard-library module.  Core-safe options may execute there.
When a requested renderer is unavailable, it exits with an actionable message
such as ``install oneroll[cli]`` or ``install oneroll[tui]``; importing the
package never triggers that check.  Core, CLI, and TUI wheel installs each have
an isolated smoke test.

Cargo remains the single package-version source.  Splitting optional
dependencies must not reintroduce a second static Python version.

Compatibility and migration
---------------------------

The module-level ``roll`` and ``run`` helpers keep their existing v1 dictionary
shapes throughout 2.x.  They are compatibility adapters over a default Engine,
not a second parser or evaluator.  ``OneRoll`` is deprecated in 2.0 and is
removed no earlier than 3.0.

``roll_simple``, ``roll_multiple``, ``roll_statistics``, and
``OneRoll.roll_with_modifiers`` are also deprecated in 2.0.  ``Engine.roll``
replaces single-instruction typed use, ``Engine.run_batch`` replaces repeated
execution, and clients calculate presentation statistics from typed batch
results.  Deprecations use Python warnings and migration documentation; they
do not silently change return shapes.

The 2.x compatibility adapter uses ``compatibility_mode="v1"`` and the
RFC-0003 mapping.  New Engine instances default to ``strict_v2``.  A
compatibility mode selected at construction applies to every call and is
recorded in result metadata.

Normative machine-readable contract
-----------------------------------

This stub freezes public names, inheritance, method signatures, keyword-only
request arguments, and return types before implementation:

.. literalinclude:: ../rfcs/0004-target-api.pyi
   :language: python
   :caption: docs/rfcs/0004-target-api.pyi

This manifest drives drift tests for names, packaging, and batch protocol:

.. literalinclude:: ../rfcs/0004-api-contract.json
   :language: json
   :caption: docs/rfcs/0004-api-contract.json

The checked stub describes the target public ``oneroll`` module.  Until the
implementation lands, it is checked separately from the installed package's
current ``_core.pyi``.  Implementation issues must move target declarations
into the installed package rather than weakening this file.

Implementation sequence
-----------------------

#. Issue 19 introduces the immutable Engine shell, parse/validate boundary, and
   typed method signatures over shared Rust domain types.
#. Issues 12, 26, and 39 provide the structured exception and typed result
   objects used by every method.
#. Issue 18 adds deterministic request randomness and accepted seed forms.
#. Issue 22 adds detached execution, cancellation, deterministic batch seeds,
   shared batch budgets, and concurrency tests.
#. Issues 38, 21, 27, and 42 fill out Program execution and trace semantics
   without changing the API boundary.
#. Issues 14 and 28 split packaging and move CLI/TUI work onto worker-plus-token
   client flows.
#. Issues 29 and 30 prove migration compatibility and isolated wheel/runtime
   support, including the explicit free-threaded gate.

Every implementation slice updates Rust tests, installed-Python tests, the
RFC-0003 schema corpus, typing parity, wheel smoke tests, and user documentation
in the same change.

Rejected alternatives
---------------------

Mutable Engine state
   Reusing an RNG cursor, variable map, or counters would make results depend on
   call order and make shared Engine instances unsafe.

Executable parsed objects
   Reuse could bypass per-request resource charging and retain stale policy or
   variable assumptions.  A compiled API needs an explicit cache contract.

Python loop for batches
   Repeated crossings lose atomic shared budgets, increase overhead, and make
   cancellation and seed derivation client-dependent.

Bare list batch return
   A list loses the root seed and replay protocol and cannot describe the
   request that failed.

Core progress callbacks
   Calling arbitrary Python while Rust is detached reintroduces GIL contention,
   reentrancy, and lifetime hazards.  Clients poll a worker instead.

Mandatory core timeout
   Wall-clock limits make deterministic work depend on host speed.  Structural
   limits remain mandatory; clients and deployments supply operational
   deadlines.

Required Rich and Textual dependencies
   Presentation dependencies enlarge library and service installs and make a
   headless core import needlessly fragile.

Acceptance gate
---------------

RFC-0004 may move from Review to Accepted when:

* the target stub passes strict type checking and agrees with the manifest;
* the batch schema examples and seed vectors pass the repository quality gate;
* RFC-0001, RFC-0002, and RFC-0003 contain no conflicting lifecycle, result,
  random, or failure contract;
* issue 5 and each directly blocked child issue reference the frozen API and
  package boundary; and
* a human review confirms the public 2.0 Python boundary.

Implementation completion is not an acceptance prerequisite.  Acceptance
freezes the target that the child issues implement.

References
----------

* `PyPA: Writing pyproject.toml <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>`_
* `PyO3 0.19 guide <https://pyo3.rs/v0.19.2/>`_
* `PyO3 migration guide <https://pyo3.rs/main/migration>`_
