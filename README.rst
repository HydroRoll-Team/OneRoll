OneRoll
=======

An efficient dice expression parsing tool, based on Rust and PEG grammar.

Overview
--------

OneRoll is a high-performance dice expression parser and roller, implemented in Rust and exposed to Python via PyO3. It supports complex dice expressions, modifiers, mathematical operations, and user comments.

Features
--------

- Basic dice rolling (XdY)
- Mathematical operations: +, -, *, /, ^
- Modifiers: !, kh, kl, dh, dl, r, ro
- Bracket support
- User comments (e.g., `3d6 + 2 # Attack roll`)
- Complete error handling
- Statistical rolling and analysis
- Rich terminal UI (TUI) via `textual`
- Python SDK and CLI

Installation
------------

.. code-block:: shell

   pip install oneroll

Or build from source:

.. code-block:: shell

   maturin build
   pip install target/wheels/oneroll-*.whl

Usage
-----

Python SDK Example:

.. code-block:: python

   import oneroll

   # Basic roll
   result = oneroll.roll("3d6 + 2")
   print(result["total"])

   # With comment
   result = oneroll.roll("4d6kh3 # Attribute roll")
   print(result["comment"])

   # Use OneRoll class
   roller = oneroll.OneRoll()
   result = roller.roll("2d6! # Exploding dice")

Command Line Example:

.. code-block:: shell

   python -m oneroll "3d6 + 2"
   python -m oneroll --stats "3d6" --times 100

Terminal UI:

.. code-block:: shell

   python -m oneroll.tui

Dice Expression Syntax
----------------------

- `XdY`: Roll X dice with Y sides
- Modifiers: `kh`, `kl`, `dh`, `dl`, `!`, `r`, `ro`
- Mathematical operations: `+`, `-`, `*`, `/`, `^`
- Comments: Add with `#`, e.g., `3d6 + 2 # Attack roll`

Examples
--------

.. code-block:: python

   # Basic
   result = oneroll.roll("3d6 + 2")

   # D&D attribute roll
   result = oneroll.roll("4d6kh3 # Attribute")

   # Statistical analysis
   stats = oneroll.roll_statistics("3d6", 100)

   # Comment usage
   result = oneroll.roll("1d20 + 5 # Attack check")
   print(result["comment"])

Documentation
-------------

- Homepage: https://hydroroll.team/
- Repository: https://github.com/HydroRoll-Team/oneroll
- Docs: https://oneroll.hydroroll.team/

License
-------

AGPL-3.0

Authors
-------

HsiangNianian <leader@hydroroll.team>