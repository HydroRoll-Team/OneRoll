import importlib.metadata
import json
import subprocess
import sys
import unittest

import oneroll


class PackageVersionTests(unittest.TestCase):
    def test_runtime_version_matches_installed_distribution(self):
        self.assertEqual(
            oneroll.__version__,
            importlib.metadata.version("oneroll"),
        )

    def test_cargo_metadata_matches_installed_distribution(self):
        completed = subprocess.run(
            ["cargo", "metadata", "--no-deps", "--format-version", "1"],
            check=True,
            capture_output=True,
            text=True,
        )
        metadata = json.loads(completed.stdout)
        package = next(
            package for package in metadata["packages"] if package["name"] == "oneroll"
        )

        self.assertEqual(
            package["version"],
            importlib.metadata.version("oneroll"),
        )

    def test_cli_reports_installed_distribution_version(self):
        completed = subprocess.run(
            [sys.executable, "-m", "oneroll", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            completed.stdout.strip(),
            importlib.metadata.version("oneroll"),
        )


if __name__ == "__main__":
    unittest.main()
