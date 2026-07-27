# OneRoll

OneRoll is a Rust dice-language engine exposed to Python through PyO3. It ships
with a Python SDK, CLI, and Textual TUI. The v2 package boundary will make UI
dependencies optional for SDK-only installations.

The current `1.x` engine supports numeric dice expressions, arithmetic,
parentheses, comments, and a compatibility set of modifiers. The `2.0` roadmap
evolves that expression roller into a bounded, typed program language with
ranges, weighted-list dice, validators, variables, option pipelines, and
structured results.

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

Every instruction in one program shares the same evaluation budget. Invalid or
exhausted evaluations raise `ValueError` instead of hanging or panicking. The
current safe default rejects Programs with more than 1,000 instructions.

## CLI

```shell
python -m oneroll "3d6 + 2"
python -m oneroll "1d20 + 5; 2d6 # encounter"
python -m oneroll --stats "3d6" --times 100
```

## Current syntax

- Numeric dice: `XdY`
- Arithmetic: `+`, `-`, `*`, `/`, `^` (the current parser has flat precedence)
- Parentheses and one trailing `# comment`
- Parsed modifiers: `!`, `e`, `K`, `r`, `ro`, `R`, `a`, `k`, `kh`, `kl`,
  `dh`, `dl`, `u`, `s`, and `c`
- Programs: `instruction; instruction; ...`

Some modifier combinations still have compatibility-sensitive behavior. See
the language guide instead of treating the parsed-token list as final semantics.

## Roadmap and specification

- [Language guide](docs/source/language.rst)
- [Production roadmap](docs/source/roadmap.rst)
- [RFC-0001: OneRoll Program Language v2](docs/rfcs/0001-dice-program-language-v2.rst)
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
