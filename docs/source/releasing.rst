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

#. Run the complete :doc:`quality` gate and merge the release commit to protected
   ``main``.
#. Manually run the ``Build distributions`` workflow for that exact ``main``
   commit and retain its run ID.  This workflow has read-only repository
   permission and cannot publish.
#. After the version, push, and publication choices receive explicit human
   confirmation, create and push a signed annotated ``vX.Y.Z`` tag for that
   commit.
#. Manually run ``Publish Release`` from ``main`` with the tag, candidate build
   run ID, PyPI choice, and prerelease choice.  Approve the protected ``pypi``
   environment only after its verification job identifies the expected source
   and artifacts.

The version-contract test compares Cargo metadata, installed distribution
metadata, Python runtime metadata, and CLI output.  This prevents a wheel from
passing the release gate when any of those public surfaces drift.

Protected publication boundary
------------------------------

Pushing a tag does not invoke a build, GitHub Release, or registry write.  The
two manual workflows deliberately separate unprivileged construction from
privileged publication:

``Build distributions``
   Runs the reusable quality gate, builds the supported wheels and sdist, and
   retains them for 14 days.  It does not receive ``contents: write`` or an OIDC
   token.  Free-threaded wheels are not built while PyO3 0.19 is installed and
   the RFC-0004 concurrency contract is unfinished.

``Publish Release``
   Accepts a signed tag and one manual build run ID.  Before an approval prompt,
   it proves that the tag is annotated and GitHub-verified, targets protected
   ``main``, matches ``Cargo.toml`` and a non-empty dated changelog section, and
   names a successful manual ``Build distributions`` run for the same SHA.  It
   downloads those prebuilt files, rejects version drift and free-threaded
   artifacts, writes ``SHA256SUMS``, and seals one candidate artifact.

The final job is protected by the ``pypi`` environment.  It downloads only the
sealed candidate and runs no checked-out project code or build command.  It
creates a new immutable GitHub Release and, when ``publish_pypi`` is true, uses
PyPI Trusted Publishing through the short-lived GitHub OIDC identity.  Existing
GitHub Releases and registry files are never updated or skipped silently.

Repository and PyPI prerequisites
---------------------------------

Before the first publication, repository administrators must configure:

* a GitHub environment named ``pypi`` with required reviewers and deployment
  restricted to protected ``main``; and
* the ``oneroll`` PyPI Trusted Publisher for owner ``HydroRoll-Team``, repository
  ``OneRoll``, workflow ``changelog.yml``, and environment ``pypi``.

If either external control is missing, publication must fail.  A long-lived API
token is not a supported fallback.  Issue 34 retains the remaining M4 provenance,
SBOM, audit, and incident-response work.

Command sequence
----------------

After the release commit is on ``main`` and all human confirmations are recorded:

.. code-block:: console

   gh workflow run build.yml --ref main
   gh run list --workflow build.yml --event workflow_dispatch --limit 1
   git tag -s vX.Y.Z -F RELEASE_NOTES.md <verified-main-sha>
   git push origin vX.Y.Z
   gh workflow run changelog.yml --ref main \
     -f tag=vX.Y.Z \
     -f build_run_id=<successful-run-id> \
     -f publish_pypi=true \
     -f prerelease=false

The M1 specification prerelease uses ``publish_pypi=false`` and
``prerelease=true``.  The milestone/version/channel mapping remains normative in
:ref:`rfc-0005`.
