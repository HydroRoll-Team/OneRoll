.. _rfc-0003:

RFC-0003: Typed Program Results, Roll Traces, and Errors
========================================================

:Status: Review
:Target: OneRoll 2.0
:Discussion: https://github.com/HydroRoll-Team/OneRoll/issues/4
:Last updated: 2026-07-29

Summary
-------

OneRoll 2.0 returns a versioned, typed ``ProgramResult`` rather than treating
every evaluation as one integer plus display text.  A successful result is a
normalized graph with three responsibilities:

* ``InstructionResult`` records ordered public values and scalar projections;
* ``RollNode`` records every immutable numeric or list draw; and
* ``TraceNode`` records the directed acyclic graph of sources and
  transformations.

Failures use a separate versioned error envelope.  They never contain partial
instructions, roll nodes, or traces.  The checked JSON Schema and normative
examples shipped with this RFC are the serialization source of truth for Rust,
Python, CLI JSON, documentation, and conformance tests.

Context
-------

The current compatibility engine exposes ``DiceResult { expression, total,
rolls, details, comment }``.  This is sufficient for numeric v1 expressions,
but it has four structural problems:

* text, Boolean, mixed, and nested values cannot be represented by ``total``;
* flattened integer arrays lose the identity of dropped, replaced, exploded,
  grouped, painted, or bound values;
* ``details`` combines behavior with human presentation and must be parsed to
  recover provenance; and
* ``DiceError`` is converted to a ``ValueError`` string, losing phase, source
  span, resource fields, and replay metadata.

RFC-0001 freezes the runtime kinds and language semantics.  RFC-0002 freezes
request-scoped randomness, counters, cancellation, and atomic failure.  This
RFC provides the shared public data boundary required to implement both.

Goals
-----

* Represent every RFC-0001 runtime value without implicit coercion.
* Make every source draw and transformation auditable without parsing display
  strings.
* Preserve stable request-local node identity through selection, generation,
  annotation, nesting, and instruction history.
* Give Rust, Python, CLI JSON, and stored payloads the same field names and
  meanings.
* Give every public failure a stable phase, code, message, and source span when
  a source location exists.
* Version and machine-check the wire contract before implementation begins.

Non-goals
---------

* Freezing Python class names or method signatures; RFC-0004 owns that API.
* Freezing human CLI/TUI layout, colors, translated prose, or ``details`` text.
* Returning parser ASTs as evaluation results.
* Returning partial results or traces after failure in v2.0.
* Defining probability-analysis result shapes; RFC-0006 owns those payloads.
* Providing globally meaningful node identifiers across independent requests.

Normalized result graph
-----------------------

The successful envelope has this conceptual shape:

.. code-block:: text

   ProgramResult {
       schema_version: "2.0",
       kind: "program_result",
       source,
       canonical,
       comment,
       instructions: [InstructionResult],
       roll_nodes: [RollNode],
       trace_nodes: [TraceNode],
       metadata: {
           compatibility_mode,
           random,
           warnings,
       },
   }

``source`` is the exact accepted Program text.  ``canonical`` is the complete
canonical Program rendering defined by RFC-0001.  ``comment`` is either the
decoded trailing comment or JSON ``null``; it is never an empty-string
sentinel in the v2 contract.

``instructions`` contains source-order top-level results.  Nested body
activations remain below the instruction that activated them.  ``roll_nodes``
and ``trace_nodes`` are normalized request-wide pools so identity is never
changed by copying a value into a collection or nested result.

The three identifier namespaces are independent:

* instruction activations are ``i0``, ``i1``, and so on;
* semantic source draws are ``r0``, ``r1``, and so on; and
* trace operations are ``t0``, ``t1``, and so on.

Identifiers are allocated monotonically in deterministic evaluation order.
For the same schema version, canonical Program, variables, seed, random
protocol, compatibility mode, and policy, a successful replay produces the
same identifiers.  Identifiers are otherwise opaque and request-local; clients
must not derive meaning from their numeric suffix or compare them across
unrelated requests.

Typed values and scalar projection
----------------------------------

``Value`` is a closed tagged union in schema 2.0:

.. list-table:: Value variants
   :header-rows: 1
   :widths: 18 35 47

   * - ``kind``
     - Payload
     - Meaning
   * - ``scalar``
     - checked signed 64-bit ``value``
     - an integer runtime value
   * - ``text``
     - Unicode ``value``
     - decoded text; no implicit numeric parsing
   * - ``boolean``
     - JSON Boolean ``value``
     - validator or literal truth value
   * - ``values``
     - ordered recursive ``items``
     - an ordinary, possibly nested value collection
   * - ``roll_set``
     - ``item_kind`` plus ordered ``{node_id, annotations}`` items
     - references immutable source draws in ``roll_nodes``

``item_kind`` is ``scalar`` or ``text`` and remains present when the collection
is empty, so filtering cannot erase the source type.  The ``annotations``
object is part of a RollSet view, not a mutation of the
referenced ``RollNode``.  Schema 2.0 defines the ``color`` annotation used by
paint.  Two views may therefore reference the same source node with different
presentation annotations while retaining one source identity.

Every ``InstructionResult`` contains both ``value`` and ``scalar``.  The latter
is an explicit compatibility and arithmetic projection, not a second result:

* a Scalar projects to its own integer;
* a flat all-Scalar Values or numeric RollSet projects to its checked sum;
* an empty flat scalar Values or Scalar RollSet projects to zero; and
* Text, Boolean, mixed Values, nested Values, and text RollSets project to
  JSON ``null``.

Projection overflow is ``arithmetic.overflow``.  Consumers must inspect
``scalar`` instead of trying to infer a total from an arbitrary JSON shape.
The value stored on an instruction must equal the value on its ``trace_root``.

Instruction and nested execution results
----------------------------------------

An ``InstructionResult`` contains a unique activation ``id``, its zero-based
``index`` within its immediate Program frame, a source ``span``, canonical
text, typed value, scalar projection, trace root, and ordered ``executions``.
Top-level instructions and nested instructions use exactly the same shape.

``executions`` preserves structured control flow without flattening it into
the top-level result array:

``repeat_iteration``
   One activated repeat body.  ``index`` is the zero-based iteration.

``branch``
   One selected conditional body.  ``label`` is ``"true"`` or ``"false"``.
   A branch that is not selected has no execution record.

``function_call``
   One nested Program activation owned by a future function.  ``label`` is the
   canonical function name when present.

Each execution contains one or more ordered ``InstructionResult`` objects.
The parent instruction's Value remains the RFC-0001 function or branch result;
children expose how that result was produced.  No body is recorded for
``repeat(0; ...)`` because it was not activated.

RollNode contract
-----------------

A ``RollNode`` is one accepted semantic draw from a numeric die, inclusive
range die, or list die.  It is immutable and contains:

* a request-local ``id``;
* one atomic Scalar or Text ``value``;
* a source descriptor with source kind, owning instruction activation, source
  position, global draw position for that source, generation depth, and source
  span;
* an optional ``parent_node_id``; and
* the ``cause_trace_id`` of the source, reroll, or explode operation that made
  the draw.

``source_index`` distinguishes multiple dice sources within one instruction.
``draw_index`` increases for every accepted semantic draw from that source,
including later option-generated values.  ``generation`` is zero for original
draws and increases along a reroll or explosion chain.

An original draw has a null parent.  A reroll replacement links to the value it
replaced.  An explosion or reroll-and-add contribution links to the value that
caused the additional draw.  Replaced, discarded, or filtered nodes remain in
the pool and in an upstream trace; they are never deleted or overwritten.

RollSet order and multiplicity are semantic.  The same node may be referenced
more than once when a language operation intentionally duplicates a view, but
the pool still contains one immutable ``RollNode``.  ``unique`` operates on
typed values while provenance continues to refer to the retained first node.

Trace DAG
---------

``TraceNode`` is one typed evaluation operation.  It contains its ID, stable
kind, optional source span, input trace IDs, output Value, related roll IDs,
and kind-specific structured data.  Trace arrays are topologically ordered:
every input must refer to an earlier trace node.  Cycles and dangling
references are invalid.

The initial closed trace-kind vocabulary is:

.. list-table:: Trace kinds
   :header-rows: 1
   :widths: 20 80

   * - Kind
     - Required meaning
   * - ``literal``
     - a Scalar, Text, Boolean, or Values literal
   * - ``variable``
     - an immutable named or positional environment lookup
   * - ``source``
     - a numeric, range, or list dice source and its original draws
   * - ``arithmetic``
     - one checked scalar operator
   * - ``select``
     - keep or drop, including selected and discarded node IDs
   * - ``filter``
     - predicate filtering and its retained/discarded node IDs
   * - ``sort``
     - a stable ordering transformation
   * - ``count``
     - a scalar count with the matching source node IDs
   * - ``reroll``
     - replacement or add behavior and newly generated node IDs
   * - ``explode``
     - an explosion chain and newly generated node IDs
   * - ``merge``
     - explicit collection combination
   * - ``bind``
     - immutable reads from completed source instruction IDs
   * - ``occurrences``
     - ordered value/count aggregation
   * - ``paint``
     - node-specific color annotations
   * - ``split``
     - one-level flattening or compound-draw spreading
   * - ``group``
     - fixed-width consecutive grouping
   * - ``function``
     - a function activation such as repeat
   * - ``branch``
     - the selected true or false conditional path
   * - ``projection``
     - an explicit scalar projection when it is not the identity

``data.operation`` is the canonical operator, source, or function token.
``data.predicate`` is a canonical validator.  The selected, discarded, and
generated ID arrays record classification without changing RollNodes.
``source_instruction_ids`` records bind dependencies.  ``branch`` and
``iteration`` identify structured activations.  Paint assignments are
structured ``{node_id, key: "color", value}`` records rather than display
text.

Every ID in a trace Value, related-ID array, or data field must exist in the
appropriate request-wide pool.  A trace output does not need to repeat every
ancestor ID: clients follow ``inputs`` to recover history.  A renderer may hide
ordinary literal or projection nodes, but serialization never drops them when
trace output is requested by the v2 Engine.

RFC-0002's ``trace_nodes`` counter charges one unit for every serialized
``RollNode`` and every ``TraceNode`` before insertion.  Selection never refunds
the source nodes it classifies.  Output byte charging includes the complete
stable envelope.

Spans and canonical text
------------------------

Every span is a half-open ``[start_byte, end_byte)`` range into the exact UTF-8
``source`` bytes.  ``start_byte`` must not exceed ``end_byte`` and neither may
exceed source length.  An empty span is permitted only for a missing token at a
specific insertion point.  Public parsing and validation errors have a span
whenever the failure is attributable to Program text.

Instruction spans cover their complete source construct excluding surrounding
separator whitespace.  Source and option trace spans cover the smallest
construct that owns the operation.  Host policy, entropy, deadline, and
explicit cancellation failures have no source span unless one expression
triggered the failing work.

``canonical`` follows RFC-0001 and is never localized.  JSON object member
order is not semantic; array order is semantic.  Integers and counters are JSON
integers, never floating-point approximations.  The engine's stable output-byte
charge uses its compact UTF-8 serialization before client decoration.

Result metadata
---------------

``compatibility_mode`` is ``strict_v2`` or ``v1``.  It records the semantics
actually used, not the method name selected by a client.

``random`` is always present on success, even if no random word was consumed.
It contains the ``oneroll-chacha12-v1`` protocol, canonical 32-byte lowercase
hexadecimal seed, and consumed raw-word count from RFC-0002.  This makes literal
and failed-to-draw Programs replayable under the same request contract.

``warnings`` contains structured non-fatal diagnostics, primarily v1
compatibility notices.  Warning codes, phases, spans, and replacements have the
same meaning as errors.  A warning cannot stand in for a failed validation or
budget check.

Error envelope
--------------

A public failure serializes as:

.. code-block:: text

   {
       "schema_version": "2.0",
       "kind": "error",
       "error": {
           "phase": "parse" | "validate" | "evaluate" | "cancel",
           "code": stable_ascii_identifier,
           "message": human_readable_text,
           "span"?: { "start_byte", "end_byte" },
           "resource"?: resource_name,
           "used"?: integer,
           "requested"?: integer,
           "limit"?: integer,
           "random"?: replay_descriptor,
           "expected"?: [construct_name],
           "replacement"?: canonical_source,
       },
   }

``phase`` records where the request was rejected:

``parse``
   The source cannot form a typed syntax tree.  Codes use ``parse.*``.

``validate``
   Syntax exists but types, variables, policy, seed, cardinality, or construct
   compatibility are invalid.  Codes normally use ``validate.*``, ``policy.*``,
   or ``random.invalid_seed``.

``evaluate``
   Checked arithmetic, randomness, resource charging, or a dynamic operation
   failed.  Codes include ``arithmetic.*``, ``limit.*``, and
   ``random.entropy_unavailable``.

``cancel``
   Explicit cancellation or a client deadline won at a checkpoint.  Codes are
   ``execution.cancelled`` or ``execution.deadline_exceeded``.

Codes match ``^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$`` and are the only field
clients use for programmatic branching.  The engine's default message is
concise English and is not a compatibility key.  CLI/TUI renderers may
localize from the code and fields without modifying the structured error.

When ``resource`` is present, ``used``, ``requested``, and ``limit`` are all
present and retain RFC-0002 meanings.  ``expected`` is an ordered list of
parser-level construct names.  ``replacement`` is used by compatibility
diagnostics.  ``random`` appears after the random stream has been initialized
and records its state at failure; it contains no generated values.

Rust's public error type, Python exception attributes and ``to_dict()``, and
CLI ``--json`` use this vocabulary.  RFC-0004 may define an exception class
hierarchy, but it cannot rename these fields or change their meanings.

Atomic failure and partial traces
---------------------------------

The success and error envelopes are disjoint.  Schema 2.0 has no representation
for a partial ``ProgramResult``.  Any parse, validation, evaluation, budget,
entropy, cancellation, or deadline failure discards all instruction results,
RollNodes, and TraceNodes before returning the error envelope.

Debuggers may consume an explicitly unstable in-process observer stream, but
that stream is not serializable as this schema, is disabled by default, and is
not a public result.  Adding public partial results requires a later RFC and a
new schema version.

Serialization and versioning
----------------------------

The normative JSON Schema uses Draft 2020-12.  Every schema and example is
checked in the quality gate.  The same decoded structure is exposed as Rust
types, Python objects/dictionaries, and CLI JSON.  Producers must not add
undeclared properties to a ``2.0`` envelope.

``schema_version`` versions the result contract independently of the OneRoll
package version:

* patch releases do not change the wire shape;
* a backward-compatible optional field or trace kind requires a reviewed
  schema-minor file and explicit consumer negotiation; and
* removing, renaming, retagging, or changing a field requires a schema-major
  version and migration RFC.

OneRoll 2.x producers emit schema ``2.0`` until another schema version is
accepted.  They must continue to read stored ``2.0`` payloads for the complete
2.x support window.  Unknown schema versions fail explicitly with
``serialization.unsupported_schema``; they are never guessed from fields.

Normative machine-readable schema
---------------------------------

This file is the source of truth for field names, required properties, value
tags, integer bounds, and closed object shapes:

.. literalinclude:: ../rfcs/0003-result.schema.json
   :language: json
   :caption: docs/rfcs/0003-result.schema.json

Normative examples
------------------

The example corpus covers Scalar, Text, mixed Values, RollSet selection,
Boolean, nested repeat Programs, parse errors, and budget failure after random
work.  Every payload must validate against the schema and the graph invariants
in this RFC:

.. literalinclude:: ../rfcs/0003-examples.json
   :language: json
   :caption: docs/rfcs/0003-examples.json

Graph validation invariants
---------------------------

Schema validation is necessary but not sufficient for cross-reference and
semantic consistency.  Implementations and the shared conformance suite must
also reject a payload unless all of these hold:

#. Instruction, RollNode, and TraceNode IDs are unique in their namespaces.
#. Every span is ordered and within the UTF-8 source length.
#. Every instruction trace root exists and has exactly the instruction Value.
#. Every trace input exists earlier in topological order.
#. Every RollSet, related, selected, discarded, generated, annotation, parent,
   cause, and source-instruction reference resolves to the correct pool.
#. A RollNode parent precedes the child and generation is parent generation
   plus one; an original node has generation zero and no parent.
#. Every RollNode is reachable from at least one source/generation trace, even
   when no final value retains it.
#. ``scalar`` equals the projection rules above, using checked signed 64-bit
   arithmetic.
#. Nested execution indices are consecutive within their parent activation;
   instruction indices are consecutive within each Program frame.
#. Error envelopes contain none of the success-only graph fields.

The schema conformance test includes valid examples and deliberately mutated
invalid payloads.  Later engine implementation tests must serialize real Rust
results and installed Python results through this same validator rather than
maintaining binding-specific snapshots.

V1 compatibility mapping
------------------------

The v1 compatibility adapter remains supported throughout OneRoll 2.x.  It is
an adapter over the typed engine, not a second result model:

.. list-table:: Legacy result mapping
   :header-rows: 1
   :widths: 22 35 43

   * - V1 field
     - V2 source
     - Compatibility rule
   * - ``expression``
     - instruction ``canonical``
     - v1 spelling is preserved only where the legacy API already promises it
   * - ``total``
     - instruction ``scalar``
     - compatibility ``roll`` rejects a result whose projection is null
   * - ``rolls``
     - RollSet views plus RollNodes
     - the adapter preserves the existing nested integer shape for v1 numeric syntax
   * - ``details``
     - structured trace renderer
     - human text remains non-normative and must not be parsed
   * - ``comment``
     - Program ``comment``
     - the v1 Python adapter may retain its empty-string sentinel
   * - Program ``results``
     - Program ``instructions``
     - the v1 ``run`` adapter returns ordered legacy dictionaries

Strict-v2 ``Engine.run`` returns the new ``ProgramResult``.  RFC-0004 freezes
the exact method and class surface.  Existing ``roll`` and ``run`` behavior is
not changed merely by merging this RFC; implementation issues introduce the
adapter and migration diagnostics with executable v1 conformance coverage.

Implementation sequence
-----------------------

This RFC unlocks focused vertical issues:

#. Issue 39 introduces Value, scalar projection, instruction activation IDs,
   and shared Rust/Python serialization primitives.
#. Issue 12 replaces string-only domain errors with the spanned structured
   envelope and stable code registry.
#. Issue 21 adds base source, keep, and drop RollNodes and TraceNodes.
#. Issue 27 extends generation and count provenance to reroll and explode.
#. Issues 38 and 42 add nested Program, bind, grouping, occurrence, and paint
   result shapes without changing the envelope.
#. Issue 35 moves ``details`` generation entirely behind trace renderers.
#. RFC-0004 and issues 19 and 26 expose the same contract through the final
   Engine and Python exception APIs.

Every slice adds Rust serialization, installed-Python equality, schema
validation, graph invariants, resource charging, and documentation in the same
change.  No slice may introduce a private alternate result or error vocabulary.

Rejected alternatives
---------------------

One nested tree containing copied roll objects
   Copying a retained die into each transformation makes identity ambiguous and
   multiplies output size.  Normalized pools retain one source fact and a DAG of
   views.

Mutable RollNodes with one final status
   One final kept/dropped flag cannot describe a node kept by one intermediate
   operation and discarded by another.  Immutable nodes plus typed trace
   outputs preserve the complete path.

Display strings as provenance
   Presentation is lossy, locale-dependent, and unstable.  Renderers consume
   structured traces; core consumers never parse ``details``.

Omit ``scalar`` and let clients compute totals
   Different clients would disagree on empty, mixed, nested, overflow, and text
   behavior.  The engine publishes one checked projection or null.

Embed partial results in errors
   This violates RFC-0002 atomicity and exposes nondeterministic prefixes under
   cancellation or resource pressure.  Schema 2.0 keeps success and failure
   disjoint.

Use package version as schema version
   Package releases include implementation and documentation changes unrelated
   to stored payloads.  An independent schema version makes compatibility
   explicit.

Acceptance gate
---------------

RFC-0003 may move from Review to Accepted when:

* the checked schema and all normative examples pass the repository quality
  gate;
* RFC-0001 and RFC-0002 contain no conflicting Value, trace, random, budget, or
  atomic-failure meaning;
* issue 4 and each directly blocked child issue reference the frozen field and
  provenance contract; and
* a human review confirms the public 2.0 serialization boundary.

Implementation completion is deliberately not an RFC acceptance prerequisite.
The accepted RFC unblocks those implementation issues; their executable engine
corpora then prove conformance to this contract.
