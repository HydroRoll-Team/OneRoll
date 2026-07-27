Quality gate
============

``.github/workflows/quality.yml`` is the reusable release gate for OneRoll.  It
runs directly for pull requests and pushes to ``main`` or ``dev`` and is also
called by the wheel, documentation, and changelog workflows.  Their build,
deploy, and release jobs declare an explicit dependency on this gate.

Run the gate locally
--------------------

Use Python 3.11 or newer and a stable Rust toolchain, then run these commands
from the repository root:

.. code-block:: console

   uv sync --all-groups --frozen
   cargo fmt --all -- --check
   cargo test --all-targets --all-features
   cargo clippy --all-targets --all-features -- -D warnings -A non-local-definitions
   uv run --frozen ruff check .
   uv run --frozen ruff format --check .
   uv run --frozen mypy --strict src/oneroll
   uv run --frozen python -m unittest discover -s tests -v
   uv run --frozen sphinx-build -W --keep-going -b html docs/source docs/_build/html

The single Rust lint allowance is limited to ``non-local-definitions`` emitted
by the PyO3 0.19 attribute macro.  All other Clippy and compiler warnings fail
the gate.  Removing this compatibility allowance belongs with the planned PyO3
upgrade rather than with unrelated language changes.

Delivery dependency
-------------------

Wheel and source-distribution jobs cannot begin until the quality workflow
succeeds, and the package release also names the quality job as a direct
dependency.  Documentation deployment and changelog-based GitHub releases use
the same reusable workflow.  The focused :doc:`conformance` workflow remains a
separate, fast semantic-drift signal, while the quality gate runs the complete
Rust and installed-Python suites.
