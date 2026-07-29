Deterministic randomness
========================

OneRoll's numeric dice now use the RFC-0002 protocol
``oneroll-chacha12-v1``.  A request owns one ChaCha12 stream, maps bounded
integers with rejection sampling, and counts every raw 64-bit word including
rejected attempts.  The old per-face ``rand::random() % sides`` path no longer
exists.

Current implementation boundary
-------------------------------

The reusable Rust foundation is implemented now:

* ``RandomSeed`` accepts an unchanged 32-byte seed, expands ``u64`` values in
  little-endian order, parses an optional ``0x`` prefix plus exactly 64
  hexadecimal digits, and renders canonical lowercase hexadecimal;
* ``DiceCalculator::with_seed`` and ``with_policy_and_seed`` create a fresh
  deterministic stream for every public evaluation;
* unseeded evaluations acquire all 32 bytes from the operating system and fail
  with ``random.entropy_unavailable`` rather than using a fallback;
* ``RandomDescriptor`` records the algorithm, effective seed, and exact
  ``rng_words`` count; and
* numeric dice use the single unbiased sampler that later range, weighted-list,
  and without-replacement sources will share.

The frozen Python ``Engine(...).roll(..., seed=...)`` and CLI seed/result
envelopes are not exposed yet.  They depend on the typed result and structured
error work tracked by issues :issue:`12`, :issue:`39`, and :issue:`19`.
Compatibility helpers intentionally keep their RFC-0004 signatures instead of
adding a temporary seed API that would later need removal.

Rust example
------------

.. code-block:: rust

   use _core::{DiceCalculator, DiceParser, RandomSeed};

   let expression = DiceParser::parse_expression("4d6")?;
   let mut calculator = DiceCalculator::with_seed(RandomSeed::from_bytes([0; 32]));
   let result = calculator.evaluate_expression(&expression)?;
   let replay = calculator.random_descriptor().expect("successful request");

   assert_eq!(result.rolls, vec![vec![4], vec![4], vec![3], vec![3]]);
   assert_eq!(replay.rng_words, 4);

The calculator stores only seed configuration between calls.  Each call starts
at word zero, so equal source, policy, and seed replay independently.  A failure
before random initialization has no descriptor; a failure after a draw retains
the descriptor and consumed-word count for the structured error layer.

Verification
------------

The merge gate checks the all-zero raw words, d6 and d20 bounded vectors,
integer/hex seed normalization, exact rejection accounting, entropy failure,
and exhaustive equal-preimage behavior with a reduced-width word space:

.. code-block:: console

   cargo test --release rfc_0002_

These reference tests are mandatory when ``rand_chacha`` or ``rand_core`` is
upgraded.
