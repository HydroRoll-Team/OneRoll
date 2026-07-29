Fuzzing and property gates
==========================

OneRoll treats panic freedom, termination, deterministic replay, bounded work,
and valid dice ranges as release properties.  Example-based conformance tests
remain the semantic source of truth; property tests and fuzzing search the
larger input space around that contract.

Merge-gate properties
---------------------

The ``proptest`` suite exercises the public Rust parser and calculator with 256
cases per property.  It covers:

* numeric face ranges and aggregate totals;
* exact replay for equal policy, seed, and request;
* monotonic behavior when ``generated_values`` is relaxed;
* arbitrary bounded UTF-8 parser inputs; and
* modifier combinations under shared generation, RNG, and work limits.

Run the same optimized gate used by CI:

.. code-block:: console

   cargo test --release property_

Set ``PROPTEST_CASES`` to increase the local case count.  A failing case is
automatically shrunk; retain the minimal input as an example regression or a
fuzz corpus entry before fixing it.

Fuzz targets
------------

``parse_program`` sends bounded UTF-8 Programs and varying parser limits
through ``DiceParser::parse_program_with_policy``.  ``evaluate_program`` also
derives a seed and resource-policy values from each input, then executes any
accepted Program through one seeded ``DiceCalculator`` request.

Both targets reject inputs above 4 KiB of source.  Generated values, RNG words,
collections, work, and output are capped inside the evaluator harness, so an
explosion or reroll sequence cannot create an unbounded fuzz iteration.

Install the pinned runner and use a nightly Rust toolchain:

.. code-block:: console

   cargo install cargo-fuzz --version 0.13.2 --locked
   cargo +nightly fuzz run parse_program -- -max_total_time=60 -timeout=5
   cargo +nightly fuzz run evaluate_program -- -max_total_time=60 -timeout=5

Intel macOS Command Line Tools installations that do not discover the SDK's
libc++ headers may need the SDK include paths for the build command:

.. code-block:: console

   CXX=/Library/Developer/CommandLineTools/usr/bin/clang++ \
   CXXFLAGS="-isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk -isystem /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/c++/v1" \
   cargo +nightly fuzz build

Scheduled campaign and regressions
----------------------------------

The ``Fuzz`` GitHub Actions workflow runs both targets every Monday at 02:17
UTC and on manual dispatch.  Each target runs for 120 seconds, each generated
case has a five-second timeout, RSS is capped at 2 GiB, and the complete job is
limited to ten minutes.  Failure artifacts are uploaded from
``fuzz/artifacts/<target>``.

Every distinct crash, timeout, or invariant failure must be minimized and
copied into ``fuzz/corpus/<target>/`` with a descriptive name in the fixing
commit.  The repository starts with regressions for empty instructions, deep
parentheses, unbounded explode/reroll forms, and checked arithmetic overflow.
