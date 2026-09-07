OneRoll
=======

OneRoll is a Rust dice-language engine with Python bindings, a command-line
interface, and a Textual interface.  The current ``1.x`` line is a bounded
expression roller; the ``2.0`` design evolves it into a typed program
language for dice and weighted-list evaluation.

Project status
--------------

The package is under active hardening.  Basic numeric dice, arithmetic,
parentheses, comments, a subset of modifiers, checked signed 64-bit arithmetic,
and the request-scoped ChaCha12 random core work today.  The complete v2
language, Python ``Engine`` seed surface, typed result graph, and final
production release gates are planned work and must not be treated as current
behavior.  RFC-0003 structured exceptions work today across Rust, Python, and
CLI JSON while preserving ``ValueError`` compatibility.

The first forward-compatible v2 slice is available through ``run``:

.. code-block:: python

   import oneroll

   program = oneroll.run("1d20 + 5; 2d6 # encounter")
   totals = [result["total"] for result in program["results"]]
   assert program["comment"] == "encounter"

Use ``roll`` for a single legacy-compatible expression and ``run`` for one or
more semicolon-separated instructions.  One program execution shares a single
evaluation budget.

Documentation
-------------

.. toctree::
   :maxdepth: 2

   language
   limits
   randomness
   fuzzing
   conformance
   quality
   deployment
   releasing
   roadmap
   rfc-0001
   rfc-0002
   rfc-0003
   rfc-0004
   rfc-0005
   rfc-0006

Source and planning
-------------------

* `Repository <https://github.com/HydroRoll-Team/OneRoll>`_
* `Milestones <https://github.com/HydroRoll-Team/OneRoll/milestones>`_
* `Issues <https://github.com/HydroRoll-Team/OneRoll/issues>`_
