# OneRoll v2 LLM Surface Corpus

## Purpose

This corpus supports the usability and LLM tool-call recall investigation in
OneRoll issue #51. It provides a deterministic way to measure how reliably a
system maps natural-language intent to the accepted OneRoll v2 surface syntax.
It is provider neutral and does not bind an LLM or provider SDK into OneRoll
core.

RFC-0001 remains authoritative. The corpus references RFC-0001 and does not
define new language syntax or semantics.

## What This Corpus Is

The corpus contains bilingual natural-language prompts and RFC-0001 canonical
expression oracles. The JSON Schema and repository contract tests enforce its
stable structure, bilingual pairing, RFC references, and target grammar
validity.

## What This Corpus Is Not

This corpus is not:

- an RFC amendment;
- a current-runtime conformance corpus;
- a model leaderboard;
- a semantic-equivalence specification; or
- a prompt-engineering template.

In particular, successful parsing by the RFC-0001 target grammar does not mean
that the current OneRoll runtime implements or accepts every corpus expression.
The Rust contract test uses the embedded target `V2TargetParser`; it does not
exercise the current `DiceParser`, Python API, or CLI runtime.

## Why Exact Canonical Expressions

Exact canonical matching is a conservative and reproducible first metric. It
keeps the oracle deterministic and makes changes reviewable without assuming a
complete v2 typed runtime or a semantic-equivalence checker.

A generated expression can be valid under the target grammar while differing
from the canonical oracle. A future evaluator may record that candidate as
grammar-valid, but this corpus does not automatically classify it as
semantically equivalent. Such a decision requires a future v2 semantic
evaluator or human review.

## Metrics Boundary

The first evaluation phase may report:

- `exact_canonical_match`: the candidate string exactly equals the canonical
  oracle;
- `target_grammar_valid`: the candidate parses with the accepted RFC-0001
  target grammar.

It must not report `semantic_accuracy` until a complete typed runtime or a
semantic-equivalence evaluator can support that claim.

## Provider Runner Contract

A future runner should emit provider-neutral JSON Lines with one candidate per
case:

```json
{"case_id":"numeric_dice.en","expression":"2d6"}
```

No provider runner, model API call, network access, or nondeterministic model
test is included here.

## Local Validation

```bash
uv run --frozen python -m unittest tests.test_llm_surface_contract -v
cargo test v2_target_grammar_parses_llm_surface_corpus -- --nocapture
```
