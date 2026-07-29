OneRoll
=======

OneRoll is a Rust dice-language engine with Python bindings, a command-line
interface, and a Textual interface.  The current ``1.x`` line is a bounded
expression roller; the ``2.0`` design evolves it into a typed program
language for dice and weighted-list evaluation.

Project status
--------------

The package is under active hardening.  Basic numeric dice, arithmetic,
parentheses, comments, and a subset of modifiers work today.  The v2 language,
deterministic randomness, structured error objects, and production release
gates are planned work and must not be treated as current behavior.

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
   conformance
   quality
   releasing
   roadmap
   rfc-0001
   rfc-0002

Source and planning
-------------------

* `Repository <https://github.com/HydroRoll-Team/OneRoll>`_
* `Milestones <https://github.com/HydroRoll-Team/OneRoll/milestones>`_
* `Issues <https://github.com/HydroRoll-Team/OneRoll/issues>`_
