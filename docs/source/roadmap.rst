Production roadmap
==================

OneRoll is moving toward a Python-first, deterministic, bounded, and auditable
dice-language engine.  The CLI is the reference client; M3 makes the Textual
interface an optional package/client boundary.

Milestones
----------

M0 — v1.3.5 Safety Baseline
   Bound every source of generated faces, capture v1 behavior, and require
   tests, lint, typing, and strict documentation checks.

M1 — v2.0 Specification Freeze
   Accept the language, execution, result/error, Python API, verification, and
   analysis RFCs.  No new syntax enters Core Alpha without a normative example
   and error case.

M2 — v2.0 Core Alpha
   Deliver the typed ``Program → Instruction → Expression`` engine, arithmetic
   precedence, typed values and variables, numeric/range/list dice, validators,
   deterministic option pipelines, seeded randomness, and shared budgets.

M3 — v2.0 Python Beta
   Expose one typed Engine API, program execution, functions and conditional
   blocks, bounded batches, CLI integration, and optional TUI dependencies.

M4 — v2.0 Release Candidate
   Complete compatibility diagnostics, migration documentation, wheel coverage,
   fuzz/property gates, and the secure release path.

M5 — v2.0 General Availability
   Publish production artifacts only after all release evidence is reproducible
   from a clean checkout.

M6 — v2.1 Probability Analysis
   Add exact analysis only for an explicit support matrix; use deterministic
   sampling everywhere else.

Delivery rule
-------------

Each implementation issue must be a vertical, executable slice through grammar,
AST, validation, evaluation, Rust/Python results, CLI behavior where applicable,
tests, and user documentation.  Parser-only or documentation-only claims do not
make a language feature complete.
