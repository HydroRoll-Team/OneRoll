# OneRoll

OneRoll is a Rust dice-language engine exposed to Python through PyO3. It ships
with a Python SDK, CLI, and Textual TUI. The v2 package boundary will make UI
dependencies optional for SDK-only installations.

The current `1.x` engine supports numeric dice expressions, arithmetic,
parentheses, comments, and a compatibility set of modifiers. The `2.0` roadmap
evolves that expression roller into a bounded, typed program language with
ranges, weighted-list dice, validators, variables, option pipelines, and
structured results.

Current scalar literals and totals use checked signed 64-bit arithmetic.
Overflow, division by zero, and invalid exponents raise `ValueError` with a
stable `arithmetic.*` code instead of panicking or wrapping.

> OneRoll is being hardened for production. Features listed in the v2 RFC are
> targets unless the implementation status explicitly says otherwise.

## Install

```shell
pip install oneroll
```

Build an editable package from source:

```shell
uv sync --frozen
uv run maturin develop
```

## Python

Use `roll()` for one compatibility expression:

```python
import oneroll

result = oneroll.roll("4d6kh3 # attribute")
print(result["total"])
print(result["comment"])
```

Use `run()` for a non-empty semicolon-separated program:

```python
program = oneroll.run("1d20 + 5; 2d6 # encounter")
print([result["total"] for result in program["results"]])
print(program["comment"])
```

Every instruction in one program shares the same request budget. Invalid or
exhausted evaluations raise `ValueError` instead of hanging or panicking.
Parsing, recursion, generated values, collections, output, work, and batches
all have safe defaults and non-disableable hard ceilings.

Create an immutable policy when an embedding needs lower limits:

```python
policy = oneroll.ResourcePolicy().with_limit("generated_values", 2_000)
roller = oneroll.OneRoll(policy)
print(policy.limits())
```

## CLI

```shell
python -m oneroll "3d6 + 2"
python -m oneroll "1d20 + 5; 2d6 # encounter"
python -m oneroll --stats "3d6" --times 100
python -m oneroll --show-limits
python -m oneroll --limit generated_values=2000 "20d6"
```

## Current syntax

The parser's authoritative accepted syntax lives in
[`src/oneroll/grammar.pest`](src/oneroll/grammar.pest) and is embedded directly
in the [language guide](docs/source/language.rst). Observable `1.x` semantics
are recorded in the [conformance corpus](tests/conformance/v1.json), including
compatibility-sensitive behavior and known defects.

## Roadmap and specification

- [Language guide](docs/source/language.rst)
- [Resource limits](docs/source/limits.rst)
- [Production roadmap](docs/source/roadmap.rst)
- [RFC-0001: OneRoll Program Language v2](docs/rfcs/0001-dice-program-language-v2.rst)
- [RFC-0002: Execution Safety, Budgets, and Randomness](docs/rfcs/0002-execution-safety-budgets-randomness.rst)
- [RFC-0003: Typed Program Results, Roll Traces, and Errors](docs/rfcs/0003-typed-results-traces-errors.rst)
- [RFC-0004: Python Engine API and Package Boundary](docs/rfcs/0004-python-engine-api-package-boundary.rst)
- [GitHub milestones](https://github.com/HydroRoll-Team/OneRoll/milestones)
- [GitHub issues](https://github.com/HydroRoll-Team/OneRoll/issues)

The implementation order is `Program → typed values → dice sources →
validators → option pipelines → functions and conditionals`. CLI commands such
as `help` and `la` stay outside the pure core language, and `@` remains reserved
until bounded jump semantics are accepted.

## Verify

```shell
cargo test
uv run --frozen maturin develop
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen sphinx-build -W --keep-going -b html docs/source docs/_build/html
```

## License

AGPL-3.0
