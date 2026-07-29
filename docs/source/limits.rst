Resource limits
===============

OneRoll applies one immutable resource policy to every Rust, Python, CLI, and
TUI request.  Free functions use the safe defaults.  A configured ``OneRoll``
instance may select any non-negative value up to the process hard maximum; a
request cannot disable a ceiling.

Python API
----------

``ResourcePolicy`` is immutable.  ``with_limit`` returns a new policy, so a
shared default or an existing roller cannot be changed accidentally:

.. code-block:: python

   import oneroll

   defaults = oneroll.ResourcePolicy()
   policy = defaults.with_limit("generated_values", 2_000)
   roller = oneroll.OneRoll(policy)

   assert defaults.limits()["generated_values"] == 10_000
   assert policy.limits()["generated_values"] == 2_000
   assert policy.hard_limits()["generated_values"] == 1_000_000

``roll_multiple`` and ``roll_statistics`` are one request.  Their samples share
the same counters; splitting work into a batch does not create fresh budgets.
The same rule applies to semicolon-separated instructions and nested
expressions.

CLI and TUI
-----------

The CLI prints its active values as machine-readable JSON and accepts repeated
overrides.  Overrides are also passed into ``--tui``.

.. code-block:: console

   $ oneroll --show-limits
   $ oneroll --limit source_bytes=4096 --limit generated_values=2000 "20d6"
   $ oneroll --limit generated_values=2000 --tui

An unknown name reports ``policy.invalid_limit``.  A value above the hard
maximum reports ``policy.limit_above_hard_max`` before execution.

Policy matrix
-------------

The values below implement the RFC-0002 matrix.  ``environment_*`` counters
currently remain at zero because the v1 API has no host-variable input, and
``trace_nodes`` remains at zero because v1 has no trace output.  They are
already configurable so those APIs cannot launch without a ceiling.  All other
rows are charged by the current parser, evaluator, batch path, or result
serializer.

.. list-table:: Default resource policy
   :header-rows: 1
   :widths: 25 18 18 39

   * - Resource
     - Default
     - Hard maximum
     - Current charging point
   * - ``source_bytes``
     - 65,536
     - 1,048,576
     - Complete UTF-8 input before parsing
   * - ``environment_items``
     - 1,024
     - 16,384
     - Reserved; v1 has no environment input
   * - ``environment_bytes``
     - 1,048,576
     - 16,777,216
     - Reserved; v1 has no environment input
   * - ``parse_depth``
     - 64
     - 256
     - Nested delimiters before Pest parsing
   * - ``ast_nodes``
     - 4,096
     - 65,536
     - Complete typed Program tree
   * - ``parsed_instructions``
     - 1,000
     - 10,000
     - All instructions in one Program
   * - ``executed_instructions``
     - 10,000
     - 1,000,000
     - Every instruction or batch-sample activation
   * - ``nesting_depth``
     - 32
     - 128
     - Active evaluator recursion
   * - ``source_items``
     - 10,000
     - 100,000
     - Requested dice before allocation
   * - ``generated_values``
     - 10,000
     - 1,000,000
     - Every initial, exploded, or rerolled value
   * - ``rng_words``
     - 20,000
     - 2,000,000
     - Every current raw random draw
   * - ``collection_items``
     - 10,000
     - 100,000
     - Live roll, Program-result, or batch collection
   * - ``trace_nodes``
     - 20,000
     - 200,000
     - Reserved; v1 does not emit traces
   * - ``output_items``
     - 10,000
     - 100,000
     - Result roots and externally visible values
   * - ``output_bytes``
     - 8,388,608
     - 67,108,864
     - Internal JSON encoding of the result
   * - ``work_units``
     - 1,000,000
     - 50,000,000
     - AST evaluation, generation, and modifier scans
   * - ``batch_samples``
     - 10,000
     - 1,000,000
     - Requested samples before batch allocation

Failure behavior
----------------

Limit failures are atomic: the API raises ``ValueError`` and returns no partial
Program or batch.  Machine-readable codes use ``limit.<resource>``; for
example, ``limit.source_bytes`` and ``limit.generated_values``.  The error text
also reports the units already used, the rejected charge, and the active
limit.  Error objects will gain structured fields under RFC-0003 without
changing these codes.

Benchmarking the defaults
-------------------------

The repository includes a dependency-free benchmark that exercises the
instruction boundary, generated-value boundary, an otherwise infinite
explosion, and a shared batch:

.. code-block:: console

   uv run --frozen python benchmarks/resource_limits.py

The benchmark emits JSON, including the active policy and elapsed milliseconds,
so release jobs can retain comparable artifacts without hard-coding a
machine-dependent timing threshold.  Boundary correctness remains enforced by
the deterministic Rust and Python test suites.
