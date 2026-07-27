Release versioning
==================

``Cargo.toml`` is the only authoritative package-version source.  A release
changes ``[package].version`` exactly once; no Python file or CLI source should
contain a separately maintained OneRoll version.

The remaining version surfaces are derived automatically:

* maturin reads the Cargo package version for wheel and source-distribution
  metadata because ``pyproject.toml`` declares ``version`` as dynamic;
* the ``oneroll._core`` extension exports Rust's compile-time
  ``CARGO_PKG_VERSION``;
* ``oneroll.__version__`` re-exports the extension value; and
* ``python -m oneroll --version`` reads ``oneroll.__version__``.

Version update path
-------------------

#. Edit only ``[package].version`` in ``Cargo.toml``.
#. Update ``CHANGELOG.md`` for the release.
#. Rebuild the installed extension and run the version contract:

   .. code-block:: console

      uv run --frozen maturin develop
      uv run --frozen python -m unittest discover -s tests -p 'test_package_version.py' -v
      uv run --frozen python -m oneroll --version

#. Run the complete :doc:`quality` gate.
#. Create a ``vX.Y.Z`` tag whose numeric component exactly matches the value in
   ``Cargo.toml``.  The tag starts the artifact and changelog workflows.

The version-contract test compares Cargo metadata, installed distribution
metadata, Python runtime metadata, and CLI output.  This prevents a wheel from
passing the release gate when any of those public surfaces drift.
