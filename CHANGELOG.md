# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.3.5] - 2026-07-30
### Security
- Remove the legacy `setup.py` bootstrap path identified by the upstream security report ([`c460b64`](https://github.com/HydroRoll-Team/OneRoll/commit/c460b64dcd90a0a64b6940edcfa9d045d2c68c1c)).
- Require GitHub-verified signed tags, protected `main` ancestry, immutable prebuilt candidates, environment approval, and PyPI Trusted Publishing OIDC ([`686b2ca`](https://github.com/HydroRoll-Team/OneRoll/commit/686b2ca072efbd95bd3bb26c2e957a25f39e855a)).

### New Features
- Enforce bounded parsing and evaluation workloads across Rust and Python entry points ([`4b65b60`](https://github.com/HydroRoll-Team/OneRoll/commit/4b65b601a7999c869a5c0179801e78bfb9977e2d), [`841934c`](https://github.com/HydroRoll-Team/OneRoll/commit/841934cd7fcb5d689b1d5a32d790950054e47f3c), [`997175e`](https://github.com/HydroRoll-Team/OneRoll/commit/997175e215f636568e98f3d294c115f39aaf9850)).
- Add deterministic ChaCha12 randomness with stable seeded behavior ([`79a3793`](https://github.com/HydroRoll-Team/OneRoll/commit/79a379326e56ee7928c6326e5b0347dd4a307c7e)).

### Bug Fixes
- Reject integer overflow with checked `i64` arithmetic ([`394062d`](https://github.com/HydroRoll-Team/OneRoll/commit/394062d0a69e410eb4f41f31a077e8114556b61e)).
- Derive Rust, Python, distribution, and CLI versions from the Cargo package version ([`97abe38`](https://github.com/HydroRoll-Team/OneRoll/commit/97abe38e746e0f6303039f7240cea7f8704db497)).
- Rebuild the editable extension before version-contract tests so cached metadata from the previous release cannot mask package-version drift.
- Use supported Intel macOS runners and current Node 24 artifact actions in the distribution pipeline ([`fde34b1`](https://github.com/HydroRoll-Team/OneRoll/commit/fde34b15652826a21997325b6cafb3c993bdf963), [`b2d5493`](https://github.com/HydroRoll-Team/OneRoll/commit/b2d549342333d01b44b7e860e94f785a40b568ab)).

### Verification
- Add a v1 conformance corpus plus checked-arithmetic, deterministic-randomness, property, and fuzz gates ([`6787313`](https://github.com/HydroRoll-Team/OneRoll/commit/67873131f4b79bdfaafe71c9ea0c4829afaa86e6), [`5bc93ac`](https://github.com/HydroRoll-Team/OneRoll/commit/5bc93acf01b1b39546f43630155e645f38672263), [`537c7b0`](https://github.com/HydroRoll-Team/OneRoll/commit/537c7b07ddebd9f8ae250ecd0d64416502c04baf)).
- Enforce formatting, tests, Clippy, Ruff, strict mypy, strict documentation, conformance, fuzzing, and a 15-target wheel/source-distribution matrix in CI ([`ce7ee72`](https://github.com/HydroRoll-Team/OneRoll/commit/ce7ee72793b65b409989eb121e85c3149b9a08c6)).

### Documentation
- Make the pest grammar executable and the single documentation source of truth, with frozen v2 language, typed result, Python API, verification, release, and probability-analysis contracts ([`d0ec68a`](https://github.com/HydroRoll-Team/OneRoll/commit/d0ec68acd5453cb9be0c2524a51d6abc684ff2f5), [`8edbd50`](https://github.com/HydroRoll-Team/OneRoll/commit/8edbd5092a3f8f69c75fa229d8c75debb631829c), [`0ee6b04`](https://github.com/HydroRoll-Team/OneRoll/commit/0ee6b047483b3393d1d14750153dd3c58d98f1ab), [`989af9c`](https://github.com/HydroRoll-Team/OneRoll/commit/989af9c21319aba5638703991301b3c626883cf7), [`fb139aa`](https://github.com/HydroRoll-Team/OneRoll/commit/fb139aa08db452d09d33f79770d11ac39763fecb), [`bf2feeb`](https://github.com/HydroRoll-Team/OneRoll/commit/bf2feeb610510ebfe1d7e1434a6d483fa034fec6)).

### Governance
- Establish repository-wide ownership with `@fu050409` as the required Code Owner ([`43d0a95`](https://github.com/HydroRoll-Team/OneRoll/commit/43d0a95596eae61531c9c1c9f57cfda03f831a68)).

## [v1.3.4] - 2025-10-14
### New Features
- [`02c240c`](https://github.com/HydroRoll-Team/OneRoll/commit/02c240c3be438feddd43a1f8597b9d64c19ef72e) - add new CI workflow for build and release process *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*

### Bug Fixes
- [`7736a99`](https://github.com/HydroRoll-Team/OneRoll/commit/7736a992b51e4b2fcb59444b00d6a019bacb0d45) - update CI workflow name and Python version for wheel building *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`5af2ef4`](https://github.com/HydroRoll-Team/OneRoll/commit/5af2ef42404b81ebd8a9110a48a7c5377e974340) - update package version to 1.3.4 in Cargo.toml *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*


## [v1.3.3] - 2025-10-14
### New Features
- [`9064943`](https://github.com/HydroRoll-Team/OneRoll/commit/9064943ad8519585df0e1d8502b43bdea42bd767) - remove FEATURE_DEVELOPMENT_EXAMPLE.md as part of project cleanup *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`8e6fdbf`](https://github.com/HydroRoll-Team/OneRoll/commit/8e6fdbf4cf68185ab9318637af0c40cdb5f66b48) - add Sphinx configuration and index file for documentation setup *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`12c771a`](https://github.com/HydroRoll-Team/OneRoll/commit/12c771ae7152520f7465e96e600daed4abf14ddc) - add GitHub Actions workflow for building and deploying documentation *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`c79ded4`](https://github.com/HydroRoll-Team/OneRoll/commit/c79ded44babda43d13fdc9ccd5b45aa397fa1a1a) - update Makefile to use ppm for Sphinx commands *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`e03dbc1`](https://github.com/HydroRoll-Team/OneRoll/commit/e03dbc1746ae2e502a2e15f316dbc7ab0ed7b6fd) - add LaTeX dependencies installation and fix publish directory path in GitHub Actions workflow *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`0feea29`](https://github.com/HydroRoll-Team/OneRoll/commit/0feea294ff710a682395208fed0580d9aa9d730a) - replace LaTeX dependencies installation step with texlive-action and update GitHub token reference *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`fac7efb`](https://github.com/HydroRoll-Team/OneRoll/commit/fac7efb7cf27425fe58dda2f3dbbb1868a647548) - add latexonly target to Makefile for building LaTeX from existing sources and update workflow to use it *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`2525e89`](https://github.com/HydroRoll-Team/OneRoll/commit/2525e8916570951a3aceaf9e922c8c1408ca101c) - enhance documentation build process with rinoh support and update dependencies *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`7cb43ca`](https://github.com/HydroRoll-Team/OneRoll/commit/7cb43cacc7652bfd4f1f08f06b83b9b21f9921d3) - expand documentation with detailed dice expression grammar and usage examples *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*

### Bug Fixes
- [`22557ab`](https://github.com/HydroRoll-Team/OneRoll/commit/22557ab6f02f11e9e480d4df5c61509b70f5dc0e) - correct action version for GitHub Pages deployment in workflow *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`f1431ca`](https://github.com/HydroRoll-Team/OneRoll/commit/f1431ca86a1500e3e89fa84c4c1c0b49bbbe488e) - update .gitignore to include Vscode settings and ensure proper formatting *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`ef254f5`](https://github.com/HydroRoll-Team/OneRoll/commit/ef254f501e29ab8ae125e0c4fb6c6d3d4282fe20) - remove unnecessary make command from LaTeX build step *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`4b82c92`](https://github.com/HydroRoll-Team/OneRoll/commit/4b82c92e05080208aa6b6f00d60100473969b0e0) - update package version to 1.3.3 in Cargo.toml *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*

### Refactors
- [`39beff8`](https://github.com/HydroRoll-Team/OneRoll/commit/39beff88ff42ec9f8365100ab1724dff2e7dd1ea) - update GitHub Actions workflow to build LaTeX PDF directly and remove latexonly target from Makefile *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*

### Chores
- [`2e7cff9`](https://github.com/HydroRoll-Team/OneRoll/commit/2e7cff9561b439485d3bff4d0cad4d0251ee7d24) - remove README.rst as part of project restructuring *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`cbdf86c`](https://github.com/HydroRoll-Team/OneRoll/commit/cbdf86cbf4f2cd4064e8ee6b73c65e6958ad15b4) - update README file reference from README.rst to README.md *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`93d462c`](https://github.com/HydroRoll-Team/OneRoll/commit/93d462c41cf0ed359475f07578bac511a329c580) - specify markdown content type for README in pyproject.toml *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`6ba4462`](https://github.com/HydroRoll-Team/OneRoll/commit/6ba44621ae1b289e07562108164bd0419ccf6d75) - remove unused Optional import from __init__.py *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`4abce3a`](https://github.com/HydroRoll-Team/OneRoll/commit/4abce3ad753d5a54ee57da588313bc4486a141ec) - add debug output for dependency installation and documentation build steps *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*


## [v1.3.2] - 2025-09-12
### New Features
- [`183e39d`](https://github.com/HydroRoll-Team/OneRoll/commit/183e39d9ebfe6e48e5ce666dee36b5347d47f53e) - add unique modifier to dice calculations and parsing *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`899ca82`](https://github.com/HydroRoll-Team/OneRoll/commit/899ca820e34b1b62190e88da71cf734295974a19) - enhance dice modifiers with new options for aliasing, sorting, and counting *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`2778db8`](https://github.com/HydroRoll-Team/OneRoll/commit/2778db81c6973078dc0e8e04c4bb711143aef84d) - add new reroll modifiers for enhanced dice functionality *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*

### Refactors
- [`745f886`](https://github.com/HydroRoll-Team/OneRoll/commit/745f886017e1a25be00a3d0634cd802126d936cd) - simplify grammar rules by removing unnecessary whitespace and comments *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*

### Chores
- [`b5d9371`](https://github.com/HydroRoll-Team/OneRoll/commit/b5d9371d47f5e9b5789f746241eaa5bd4222314d) - update CI configuration for maturin v1.8.6 and enhance wheel building steps *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`b0a8fe3`](https://github.com/HydroRoll-Team/OneRoll/commit/b0a8fe3c3d28644bff9432abb68aa817d0db14ed) - update Python version to 3.11 in CI configuration *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`b8fa777`](https://github.com/HydroRoll-Team/OneRoll/commit/b8fa77736a3c3b9c9d898e7ffa87e057cfab005d) - update Python version in CI configuration to use 3.x for compatibility *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*
- [`88a6ddc`](https://github.com/HydroRoll-Team/OneRoll/commit/88a6ddcd196cc95964a8abc9c247884ece9028f6) - bump version into 1.3.2 *(commit by [@HsiangNianian](https://github.com/HsiangNianian))*

[v1.3.2]: https://github.com/HydroRoll-Team/OneRoll/compare/v1.0.2...v1.3.2
[v1.3.3]: https://github.com/HydroRoll-Team/OneRoll/compare/v1.3.2...v1.3.3
[v1.3.4]: https://github.com/HydroRoll-Team/OneRoll/compare/v1.3.3...v1.3.4
