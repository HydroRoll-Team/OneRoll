v1 conformance corpus
=====================

OneRoll records the observable ``1.x`` language contract in
``tests/conformance/v1.json``.  This file is the shared source of truth for the
Rust engine and the installed Python package; a behavior change cannot silently
pass in one binding while failing in the other.

The corpus covers every syntax family listed in :doc:`language`, including
literals, numeric dice, arithmetic, parentheses, comments, every v1 modifier,
modifier composition, semicolon-separated programs, resource-limit failures,
and representative parse and evaluation errors.

Behavior classifications
------------------------

``intended``
   Behavior that the current implementation deliberately guarantees.

``compatibility_sensitive``
   Observable v1 behavior that a v2 design may change only with an explicit
   migration decision.  Every such case links to a tracking issue.

``known_defect``
   Reproducible current behavior that is deliberately captured but must not be
   interpreted as the target design.  Examples include flat operator
   precedence (:issue:`16`) and incomplete ``K`` semantics (:issue:`24`).

The corpus uses deterministic expressions such as ``d1``.  It compares totals,
the number of generated values, comments, and stable error fragments rather
than random face values or presentation text.

Run the contract locally
------------------------

From the repository root:

.. code-block:: console

   cargo test rust_engine_matches_v1_conformance_corpus
   uv run --frozen maturin develop
   uv run --frozen python -m unittest tests.test_v1_conformance -v

The dedicated ``V1 Conformance`` workflow runs the same focused checks for pull
requests and changes on ``main`` or ``dev``.  Failure output includes the case
identifier, classification, and expression so semantic drift can be reviewed
without comparing two opaque test logs.

Changing the corpus
-------------------

Add or update a case in the same change as its implementation and user
documentation.  A non-``intended`` case must include ``tracking_issue``.  Do
not reclassify or delete a compatibility-sensitive or known-defect case without
recording the language decision in its linked issue or RFC.
