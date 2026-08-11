.. _rfc-0005:

RFC-0005: Verification, Documentation, and Release
==================================================

:Status: Accepted
:Target: OneRoll 2.0
:Discussion: https://github.com/HydroRoll-Team/OneRoll/issues/2
:Last updated: 2026-07-31

Summary
-------

OneRoll releases one source revision only after that revision has produced a
machine-readable conformance result, installed-package evidence, strict public
documentation, and immutable release metadata.  Building a wheel, creating a
tag, publishing to PyPI, and publishing a GitHub Release are distinct actions;
success in one is not evidence that the others are correct.

This RFC freezes three contracts:

* one versioned corpus format records parsing, canonical text, typed values,
  traces, errors, and seeded execution for Rust and installed Python;
* documentation distinguishes implemented, experimental, and planned behavior
  and derives normative syntax from checked sources; and
* every milestone has an immutable GitHub Release, while registry publication
  is a separately approved, least-privileged action over previously verified
  artifacts.

The machine-readable corpus schema, representative cases, and release contract
are normative.  They define the target gates without claiming that every v2
feature or production publishing control is implemented today.

Current baseline
----------------

The repository already has several parts of the target system:

* ``tests/conformance/v1.json`` runs the same compatibility cases through Rust
  and the installed Python package;
* the reusable ``Quality`` workflow runs Rust and Python tests, formatting,
  linting, strict typing, and Sphinx with warnings as errors;
* property tests and bounded parser/evaluator fuzz targets are versioned;
* ``Cargo.toml`` is the only manually maintained package-version source; and
* manual candidate builds produce wheels and an sdist only after the reusable
  quality gate succeeds.

The baseline is not the final v2 release system.  It does not yet execute a v2
corpus against real typed results, install every advertised wheel, produce an
SBOM, or emit the complete M4 provenance record.  Publication is now separated
from candidate construction: arbitrary tag pushes cannot publish, free-threaded
wheels are excluded, and the manual path consumes one verified build through a
reviewer-protected ``pypi`` environment and PyPI Trusted Publishing OIDC.  The
environment protection and PyPI publisher are external controls that must be
configured before the first release.  Issues 20, 30, 34, and 37 close the
remaining gaps; this RFC defines the contract they must satisfy.

Goals
-----

* Make every supported behavior reviewable as a stable case rather than an
  implementation-specific snapshot.
* Exercise the same semantic expectations through Rust, the installed Python
  wheel, and CLI JSON where that surface applies.
* Prevent roadmap syntax or target APIs from appearing as current behavior.
* Preserve enough evidence to reproduce why a particular commit was released.
* Publish exactly the artifacts that passed installation and smoke tests.
* Require an explicit protected approval before any production registry write.
* Give every completed milestone a durable GitHub Release and release note.

Non-goals
---------

* Replacing RFC-0001 language semantics, RFC-0002 resource and randomness
  semantics, RFC-0003 result/error shapes, or RFC-0004 Python signatures.
* Requiring statistical fuzz campaigns to be bit-for-bit reproducible.
* Promising that every buildable target is supported.
* Treating a GitHub Actions success badge as permanent release evidence.
* Automatically deciding that a human-reviewed RFC or release candidate is
  acceptable.

Evidence model
--------------

One release is identified by all of the following values:

``source_sha``
   The full commit SHA on protected ``main``.  A release never targets a moving
   branch name.

``cargo_version``
   The SemVer value from ``Cargo.toml``.  The signed annotated tag is
   ``v{cargo_version}``.

``python_version``
   The canonical PEP 440 form embedded in Python distribution metadata.  Final
   versions are textually identical to the Cargo version.  Pre-release forms
   are derived, for example ``2.0.0-alpha.1`` becomes ``2.0.0a1``; the two are
   one version decision, not independently edited values.

``artifact_digest``
   A SHA-256 digest for every wheel, source distribution, SBOM, and evidence
   manifest.  Publication downloads by immutable workflow run and verifies
   these digests before uploading.

``evidence``
   Links and machine-readable summaries for each gate applicable to the
   milestone.  Evidence records command, toolchain, source SHA, conclusion,
   and artifact digest where applicable.

A release is incomplete if its tag, Cargo version, Python metadata, source SHA,
or artifact digest disagree.  Retrying publication may reuse the exact verified
artifacts; rebuilding under the same version requires a new candidate and may
not overwrite files already accepted by a registry.

Conformance corpus
------------------

One corpus format covers syntax and execution.  The schema is independent of
the package and result-schema versions so the harness can evolve without
silently changing language behavior.

.. literalinclude:: ../rfcs/0005-conformance.schema.json
   :language: json
   :caption: docs/rfcs/0005-conformance.schema.json

Each case has a globally unique ID, one tracking issue, one or more feature
families, a source Program, request inputs, and exactly one success or error
expectation.  The feature families are ``program``, ``instruction``,
``typed_value``, ``dice_source``, ``validator``, ``option``, ``function``, and
``error``.

Case lifecycle
~~~~~~~~~~~~~~

``planned``
   A normative RFC case whose schema and cross-RFC references are checked, but
   whose feature is not presented as implemented and is not executed against
   the production engine.

``required``
   An implemented contract.  Every applicable adapter must execute the case in
   pull-request and release CI.  A required case may not be skipped because a
   platform or binding disagrees.

``legacy``
   A frozen compatibility case.  It continues to run through the v1 adapter and
   records whether the behavior is intended, compatibility-sensitive, or a
   known defect with a migration target.

An implementation issue activates cases vertically.  It changes the relevant
cases from ``planned`` to ``required`` in the same change that implements the
Rust behavior, installed-Python behavior, error path, and documentation.  No
feature status can become implemented until its success and failure cases are
both required and green.

Success expectations
~~~~~~~~~~~~~~~~~~~~

A success case records:

* the canonical Program;
* a parser summary sufficient to detect instruction and node-kind drift;
* the RFC-0003 typed value and scalar projection;
* required trace kinds and stable provenance references;
* the compatibility mode; and
* the random algorithm, effective seed, and consumed-word count.

The full RFC-0003 payload remains the result source of truth.  Corpus summaries
make failures readable; they do not authorize a second result vocabulary.
Seeded cases use the canonical 32-byte seed.  Unseeded cases assert only
invariants and the returned effective seed, never a particular random value.

Error expectations
~~~~~~~~~~~~~~~~~~

An error case records phase, stable code, UTF-8 byte span, and any structured
fields required by RFC-0002 or RFC-0003.  Static parse or validation failures
also assert that zero random words were consumed.  Atomic execution failures
must not expose a success result or partial trace.

Normative format examples
~~~~~~~~~~~~~~~~~~~~~~~~~

The representative corpus below covers success and failure for every required
feature family.  It validates the format and vocabulary before the related v2
features are activated.

.. literalinclude:: ../rfcs/0005-conformance-examples.json
   :language: json
   :caption: docs/rfcs/0005-conformance-examples.json

Verification gates
------------------

Pull-request gate
~~~~~~~~~~~~~~~~~

Every change to the engine, bindings, public documentation, packaging, corpus,
or release automation must pass:

* Rust formatting, tests in debug and release where overflow or randomness can
  differ, and Clippy with warnings denied;
* installed-package Python tests, strict typing, Ruff lint and format checks;
* active v1 and v2 conformance cases through Rust and installed Python;
* deterministic property tests and bounded fuzz smoke campaigns for changed
  parser/evaluator surfaces;
* strict Sphinx HTML plus doctests for executable public examples; and
* repository contract tests for workflows, package metadata, normative
  includes, feature status, and unsupported claims.

Mandatory jobs cannot use ``continue-on-error``.  A skipped job is success only
when a checked path classifier proves that the job is inapplicable; release
evidence lists the classifier result.

Scheduled gate
~~~~~~~~~~~~~~

Scheduled CI extends, but never replaces, deterministic merge gates.  It runs
longer fuzz campaigns, fixed-threshold distribution smoke tests, dependency and
license audits, and external-link checking.  A discovered crash, hang, bias
failure, or broken supported link becomes a versioned regression input or
tracked issue before the next release candidate.

Candidate gate
~~~~~~~~~~~~~~

Release-candidate evidence is produced from a clean checkout of one full SHA.
It adds:

* isolated installation of every advertised wheel and the sdist;
* core-only, ``[cli]``, and ``[tui]`` dependency-boundary checks;
* runtime/stub export parity, shared-Engine concurrency, GIL release, and
  cross-thread cancellation tests where implemented;
* strict documentation builds from the candidate version;
* an SPDX SBOM, dependency audit, provenance attestations, and digests; and
* clean-room upgrade, CLI, SDK, and rollback smoke tests for a GA candidate.

The release workflow consumes these artifacts by digest.  It does not rebuild
source after approval.

Supported artifact matrix
-------------------------

Support means an artifact was installed and its exact smoke suite passed.  A
successful cross-build without installation is build coverage, not user-facing
support.

The v2.0 required matrix is:

* CPython 3.9 through the newest minor explicitly listed in the release
  contract, using the ``abi3-py39`` core where supported;
* manylinux x86_64 and aarch64;
* musllinux x86_64 and aarch64;
* macOS x86_64 and arm64; and
* Windows x86_64.

Other Linux architectures and Windows x86 may remain build-only until an
isolated install result is available.  They must not appear in the supported
matrix merely because the wheel builder emitted a file.

Free-threaded CPython artifacts are not published or advertised until PyO3 is
at least 0.23, exposed classes satisfy the free-threaded model, and the
dedicated concurrency and cancellation suite passes on every published target.
Issue 30 owns the executable matrix and removes targets that cannot meet it.

Documentation contract
----------------------

Public documentation has three kinds of source:

Normative
   Accepted RFCs, checked Pest grammar, JSON Schemas, API stubs, and active
   conformance cases.  These define behavior.

Operational
   Quickstarts, API guides, CLI/TUI guides, migration instructions, and release
   runbooks.  Their examples execute against the installed package and link to
   the normative decision they explain.

Planning
   Review RFCs, roadmap pages, and planned corpus cases.  They are visibly
   labelled and cannot be worded as current package behavior.

The engine grammar is included directly; documentation cannot maintain a
second syntax copy.  Result fields and Python signatures come from their
checked RFC artifacts until implementation, then from installed public
surfaces checked against those artifacts.  Broken internal references,
unknown lexers, warnings, stale grammar copies, and unsupported feature claims
fail CI.  External links run on the scheduled and candidate gates so temporary
network failure does not make local semantic tests flaky.

Feature status uses exactly ``implemented``, ``experimental``, or ``planned``.
``implemented`` requires active conformance and user documentation.
``experimental`` requires executable tests but may change before the next
accepted contract.  ``planned`` is never shown in a quickstart without an
explicit warning.

Release train
-------------

Every completed milestone produces one immutable GitHub Release.  The release
contract fixes the intended version, channel, registry policy, and cumulative
evidence:

.. literalinclude:: ../rfcs/0005-release-contract.json
   :language: json
   :caption: docs/rfcs/0005-release-contract.json

The train is:

* M0: ``v1.3.5``, the final 1.x safety baseline;
* M1: ``v2.0.0-alpha.0``, a GitHub-only specification pre-release;
* M2: ``v2.0.0-alpha.1``, the first Core Alpha package candidate;
* M3: ``v2.0.0-beta.1``, the Python Beta;
* M4: ``v2.0.0-rc.1``, the release candidate;
* M5: ``v2.0.0``, general availability; and
* M6: ``v2.1.0``, probability analysis.

Additional alpha, beta, or RC versions are allowed when a milestone requires a
replacement candidate.  Existing tags and registry files are never moved or
overwritten.  The milestone's final successful candidate is the release linked
from the milestone; superseded pre-releases remain auditable.

M1 is GitHub-only because it freezes contracts rather than claiming the typed
engine is usable.  Later pre-releases may be published to PyPI only after the
evidence applicable to their stage passes.  Python installers normally exclude
pre-releases unless explicitly requested, which keeps the stable 1.x line the
default until M5.

Publication workflow
--------------------

Publication is a separate workflow with the minimum permissions needed for its
job.  It is invoked with ``workflow_dispatch`` for one immutable candidate SHA
or signed tag and enters the protected ``pypi`` environment.  A required human
reviewer verifies version, changelog, milestone state, evidence digests, and
rollback owner before approval.

PyPI authentication uses Trusted Publishing OIDC, not a stored long-lived API
token.  The publish job receives ``id-token: write`` only after environment
approval.  GitHub Release permissions and PyPI publication permissions are
separate jobs.  Pull requests, branch pushes, arbitrary tags, scheduled runs,
and unapproved workflow dispatches cannot write to a registry.

The ordered release protocol is:

#. Freeze the milestone and resolve every required P0/P1 issue.
#. Create a release commit on protected ``main`` containing the Cargo version,
   changelog, and evidence manifest.
#. Run candidate gates from that exact commit and record artifact digests.
#. Obtain explicit publication approval.
#. Create and verify a signed annotated tag.
#. Publish the GitHub Release and, when enabled for the milestone, upload the
   already verified artifacts through the protected Trusted Publisher.
#. Verify the public tag, release, attestations, PyPI metadata, clean-room
   installs, CLI/SDK behavior, documentation, and milestone linkage.
#. Record the observation and rollback owner.

If publication partially fails, do not rebuild or reuse the version with
different bytes.  Retry only missing identical files, otherwise increment the
candidate version.  A compromised or defective release follows the runbook:
yank on PyPI when appropriate, preserve the GitHub Release with a warning,
publish a fixed version, notify affected users, and rotate or remove any
credential or publisher configuration involved.

Implementation sequence
-----------------------

#. Issue 2 lands this RFC, schema, examples, release contract, and drift tests.
#. Issues 39, 12, 40, 41, 42, and 43 activate vertical v2 corpus families as
   their runtime behavior ships.
#. Issue 20 builds task-oriented production documentation and executes every
   public example.
#. Issue 30 reduces the advertised wheel matrix to installed, tested targets
   and adds package-boundary and concurrency evidence.
#. Issue 34 separates candidate build from approval-protected Trusted
   Publishing, then adds SBOM, audits, attestations, and incident runbooks.
#. Issue 37 executes the complete candidate-to-GA protocol from public
   artifacts and records post-release ownership.

Rejected alternatives
---------------------

One snapshot suite per binding
   Rust and Python could silently disagree while each snapshot remains green.
   One semantic corpus with adapter-specific execution keeps the contract
   shared.

Treat every RFC example as implemented
   Normative target examples must exist before implementation.  The explicit
   planned-to-required lifecycle prevents them from becoming false product
   claims.

Publish directly on any tag
   Tag creation alone does not prove review, artifact identity, supported-wheel
   installation, or rollback readiness.  It is a source identity, not a
   production approval.

Rebuild during publication
   The reviewed candidate and published bytes could differ.  Publishing by
   digest preserves the tested artifact identity.

Long-lived PyPI token
   A stored credential remains useful after theft.  Trusted Publishing narrows
   identity to the repository, workflow, and environment and mints a
   short-lived token.

Advertise every generated wheel
   Cross-compilation can emit an artifact that cannot import or satisfy the
   package boundary.  Support starts with isolated installation evidence.

Acceptance gate
---------------

RFC-0005 was accepted after:

* the corpus schema accepts the normative examples and every feature family has
  both a success and error case;
* the release contract has one GitHub Release mapping for M0 through M6 and an
  explicit protected publication boundary;
* RFC-0001 through RFC-0004 contain no conflicting syntax, random, result,
  error, or Python version meaning;
* issues 20, 30, 34, and 37 reference this verification and publication
  boundary; and
* a human review confirms the supported matrix, milestone release train, and
  production approval model.

Human acceptance was recorded on 2026-07-31 through the discussion issue.

Implementation completion is not an acceptance prerequisite.  Acceptance
freezes the evidence format and release target; the mapped implementation
issues make each gate real before its milestone can close.

References
----------

* `PyPI Trusted Publishing <https://docs.pypi.org/trusted-publishers/>`_
* `PyPI Trusted Publisher security model
  <https://docs.pypi.org/trusted-publishers/security-model/>`_
* `Python version specifiers
  <https://packaging.python.org/en/latest/specifications/version-specifiers/>`_
* `GitHub artifact attestations
  <https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations>`_
* `Semantic Versioning 2.0.0 <https://semver.org/>`_
* :ref:`rfc-0001`
* :ref:`rfc-0002`
* :ref:`rfc-0003`
* :ref:`rfc-0004`
