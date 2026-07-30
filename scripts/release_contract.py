#!/usr/bin/env python3
"""Validate immutable OneRoll release candidates before publication."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - the release workflow uses Python 3.11+
    import tomli as tomllib


TAG_PATTERN = re.compile(
    r"^v(?P<version>[0-9]+\.[0-9]+\.[0-9]+"
    r"(?:-(?:alpha|beta|rc)\.[0-9]+)?)$"
)
FREE_THREADED_WHEEL = re.compile(r"-(?:cp|pp)[0-9]+t-")


class ReleaseContractError(ValueError):
    """The candidate does not satisfy the checked release contract."""


def version_from_tag(tag: str) -> str:
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise ReleaseContractError("tag must match vX.Y.Z or vX.Y.Z-(alpha|beta|rc).N")
    return match.group("version")


def python_version(cargo_version: str) -> str:
    match = re.fullmatch(
        r"(?P<base>[0-9]+\.[0-9]+\.[0-9]+)"
        r"(?:-(?P<kind>alpha|beta|rc)\.(?P<number>[0-9]+))?",
        cargo_version,
    )
    if match is None:
        raise ReleaseContractError(f"unsupported Cargo version: {cargo_version}")
    if match.group("kind") is None:
        return match.group("base")
    marker = {"alpha": "a", "beta": "b", "rc": "rc"}[match.group("kind")]
    return f"{match.group('base')}{marker}{match.group('number')}"


def read_cargo_version(cargo_toml: Path) -> str:
    try:
        with cargo_toml.open("rb") as cargo_file:
            version = tomllib.load(cargo_file)["package"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as error:
        raise ReleaseContractError(f"cannot read Cargo version: {error}") from error
    if not isinstance(version, str):
        raise ReleaseContractError("Cargo package.version must be a string")
    return version


def extract_release_notes(changelog: Path, version: str) -> str:
    try:
        lines = changelog.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError as error:
        raise ReleaseContractError(f"cannot read changelog: {error}") from error

    escaped = re.escape(version)
    heading = re.compile(
        rf"^##\s+(?:\[v?{escaped}\]|v?{escaped})\s+-\s+"
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}\s*$"
    )
    start = next(
        (index for index, line in enumerate(lines) if heading.fullmatch(line.rstrip())),
        None,
    )
    if start is None:
        raise ReleaseContractError(f"CHANGELOG.md has no dated section for v{version}")

    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    notes = "".join(lines[start:end]).rstrip() + "\n"
    body = "".join(lines[start + 1 : end]).strip()
    if not body:
        raise ReleaseContractError(f"release notes for v{version} are empty")
    return notes


def validate_source(root: Path, tag: str, notes_output: Path) -> None:
    version = version_from_tag(tag)
    cargo_version = read_cargo_version(root / "Cargo.toml")
    if version != cargo_version:
        raise ReleaseContractError(
            f"tag {tag} does not match Cargo.toml package.version {cargo_version}"
        )

    notes = extract_release_notes(root / "CHANGELOG.md", version)
    notes_output.parent.mkdir(parents=True, exist_ok=True)
    notes_output.write_text(notes, encoding="utf-8")
    print(f"validated source for {tag}; release notes: {notes_output}")


def validate_artifacts(directory: Path, tag: str) -> None:
    version = python_version(version_from_tag(tag))
    try:
        files = sorted(path for path in directory.rglob("*") if path.is_file())
    except OSError as error:
        raise ReleaseContractError(f"cannot inspect artifacts: {error}") from error

    wheels = [path for path in files if path.name.endswith(".whl")]
    sdists = [path for path in files if path.name.endswith(".tar.gz")]
    unexpected = [
        path.name for path in files if path not in wheels and path not in sdists
    ]
    if unexpected:
        raise ReleaseContractError(f"unexpected release files: {', '.join(unexpected)}")
    if not wheels:
        raise ReleaseContractError("candidate contains no wheels")
    if len(sdists) != 1:
        raise ReleaseContractError(
            f"candidate must contain exactly one sdist, found {len(sdists)}"
        )

    prefix = f"oneroll-{version}-"
    expected_sdist = f"oneroll-{version}.tar.gz"
    for wheel in wheels:
        if not wheel.name.startswith(prefix):
            raise ReleaseContractError(
                f"artifact {wheel.name} does not match Python version {version}"
            )
        if FREE_THREADED_WHEEL.search(wheel.name):
            raise ReleaseContractError(
                f"free-threaded wheel is not publishable: {wheel.name}"
            )
    if sdists[0].name != expected_sdist:
        raise ReleaseContractError(
            f"sdist {sdists[0].name} does not match {expected_sdist}"
        )

    print(f"validated {len(wheels)} wheels and 1 sdist for {tag}")


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(description=__doc__)
    subcommands = command_parser.add_subparsers(dest="command", required=True)

    source = subcommands.add_parser("source")
    source.add_argument("--root", type=Path, default=Path.cwd())
    source.add_argument("--tag", required=True)
    source.add_argument("--notes-output", type=Path, required=True)

    artifacts = subcommands.add_parser("artifacts")
    artifacts.add_argument("--tag", required=True)
    artifacts.add_argument("--directory", type=Path, required=True)
    return command_parser


def main() -> int:
    arguments = parser().parse_args()
    try:
        if arguments.command == "source":
            validate_source(arguments.root, arguments.tag, arguments.notes_output)
        else:
            validate_artifacts(arguments.directory, arguments.tag)
    except ReleaseContractError as error:
        print(f"release contract error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
