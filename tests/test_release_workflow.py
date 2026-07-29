import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE_CONTRACT = ROOT / "scripts" / "release_contract.py"


def load_workflow(name: str) -> dict[str, object]:
    return yaml.load(
        (WORKFLOWS / name).read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def workflow_commands(workflow: dict[str, object]) -> str:
    jobs = workflow["jobs"]
    return "\n".join(
        step.get("run", "")
        for job in jobs.values()
        if isinstance(job, dict)
        for step in job.get("steps", [])
        if isinstance(step, dict)
    )


class ReleaseWorkflowContractTests(unittest.TestCase):
    def test_release_actions_are_immutable_and_checkout_drops_credentials(self):
        for workflow_name in ("build.yml", "changelog.yml"):
            workflow = load_workflow(workflow_name)
            for job_name, job in workflow["jobs"].items():
                if not isinstance(job, dict):
                    continue
                for step in job.get("steps", []):
                    action = step.get("uses")
                    if not action or action.startswith("./"):
                        continue
                    with self.subTest(
                        workflow=workflow_name, job=job_name, action=action
                    ):
                        self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")
                        if action.startswith("actions/checkout@"):
                            self.assertEqual(
                                step.get("with", {}).get("persist-credentials"),
                                "false",
                            )

    def test_distribution_build_never_publishes_or_builds_free_threaded_wheels(self):
        build = load_workflow("build.yml")
        triggers = build["on"]

        self.assertNotIn("tags", triggers.get("push", {}))
        self.assertIn("workflow_dispatch", triggers)
        self.assertNotIn("release", build["jobs"])

        serialized = (WORKFLOWS / "build.yml").read_text(encoding="utf-8")
        self.assertNotIn("PYPI_API_TOKEN", serialized)
        self.assertNotIn("maturin upload", serialized)
        self.assertNotIn("python3.13t", serialized)
        self.assertNotIn("cp313t", serialized)

    def test_publication_is_manual_and_consumes_one_verified_build_run(self):
        release = load_workflow("changelog.yml")
        triggers = release["on"]

        self.assertEqual(set(triggers), {"workflow_dispatch"})
        inputs = triggers["workflow_dispatch"]["inputs"]
        self.assertEqual(
            set(inputs), {"tag", "build_run_id", "publish_pypi", "prerelease"}
        )
        self.assertEqual(inputs["tag"]["required"], "true")
        self.assertEqual(inputs["build_run_id"]["required"], "true")

        jobs = release["jobs"]
        self.assertEqual(jobs["quality"]["uses"], "./.github/workflows/quality.yml")
        self.assertIn("quality", jobs["verify"]["needs"])
        self.assertIn("verify", jobs["publish"]["needs"])

        download = next(
            step
            for step in jobs["verify"]["steps"]
            if step.get("uses", "").startswith("actions/download-artifact@")
        )
        self.assertEqual(download["with"]["run-id"], "${{ inputs.build_run_id }}")
        self.assertEqual(download["with"]["github-token"], "${{ github.token }}")
        self.assertEqual(download["with"]["pattern"], "wheels-*")

        commands = workflow_commands(release)
        self.assertIn("gh run view", commands)
        self.assertIn("actions/workflows/build.yml", commands)
        self.assertIn("workflowDatabaseId", commands)
        self.assertIn("git cat-file -t", commands)
        self.assertIn("verification.verified", commands)
        self.assertIn("git merge-base --is-ancestor", commands)
        self.assertIn('release create "${TAG}"', commands)
        self.assertIn('gh "${release_args[@]}"', commands)
        self.assertNotIn("allowUpdates", commands)

    def test_pypi_uses_one_protected_oidc_publish_job_without_secrets(self):
        release = load_workflow("changelog.yml")
        publish = release["jobs"]["publish"]

        self.assertEqual(publish["environment"]["name"], "pypi")
        self.assertEqual(publish["permissions"]["id-token"], "write")
        self.assertEqual(publish["permissions"]["contents"], "write")

        pypi = next(
            step
            for step in publish["steps"]
            if step.get("uses", "").startswith("pypa/gh-action-pypi-publish@")
        )
        self.assertEqual(pypi["if"], "${{ inputs.publish_pypi == true }}")
        self.assertEqual(pypi["with"]["packages-dir"], "release-candidate/packages")

        publish_uses = {
            step.get("uses", "") for step in publish["steps"] if isinstance(step, dict)
        }
        self.assertFalse(
            any(action.startswith("actions/checkout@") for action in publish_uses)
        )
        publish_commands = "\n".join(
            step.get("run", "") for step in publish["steps"] if isinstance(step, dict)
        )
        for forbidden in ("python scripts/", "cargo ", "maturin "):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, publish_commands)

        serialized = (WORKFLOWS / "changelog.yml").read_text(encoding="utf-8")
        self.assertNotIn("secrets.", serialized)
        self.assertNotIn("password:", serialized)
        self.assertNotIn("PYPI_API_TOKEN", serialized)
        self.assertNotIn("MATURIN_PYPI_TOKEN", serialized)

    def test_release_contract_extracts_versioned_notes_and_validates_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Cargo.toml").write_text(
                '[package]\nname = "oneroll"\nversion = "2.0.0-alpha.0"\n',
                encoding="utf-8",
            )
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n"
                "## [v2.0.0-alpha.0] - 2026-07-29\n\n"
                "### Changes\n\n- Freeze the v2 specification.\n\n"
                "## [v1.3.5] - 2026-07-28\n\n- Previous release.\n",
                encoding="utf-8",
            )
            notes = root / "RELEASE_NOTES.md"
            source = subprocess.run(
                [
                    sys.executable,
                    str(RELEASE_CONTRACT),
                    "source",
                    "--root",
                    str(root),
                    "--tag",
                    "v2.0.0-alpha.0",
                    "--notes-output",
                    str(notes),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(source.returncode, 0, source.stdout + source.stderr)
            self.assertIn("Freeze the v2 specification", notes.read_text())
            self.assertNotIn("Previous release", notes.read_text())

            packages = root / "packages"
            packages.mkdir()
            (packages / "oneroll-2.0.0a0-cp39-abi3-manylinux_2_17_x86_64.whl").touch()
            (packages / "oneroll-2.0.0a0.tar.gz").touch()
            artifacts = subprocess.run(
                [
                    sys.executable,
                    str(RELEASE_CONTRACT),
                    "artifacts",
                    "--tag",
                    "v2.0.0-alpha.0",
                    "--directory",
                    str(packages),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                artifacts.returncode, 0, artifacts.stdout + artifacts.stderr
            )

    def test_release_contract_rejects_version_drift_and_free_threaded_wheels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Cargo.toml").write_text(
                '[package]\nname = "oneroll"\nversion = "1.3.5"\n',
                encoding="utf-8",
            )
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [v1.3.5] - 2026-07-29\n\n- Safety.\n",
                encoding="utf-8",
            )
            mismatch = subprocess.run(
                [
                    sys.executable,
                    str(RELEASE_CONTRACT),
                    "source",
                    "--root",
                    str(root),
                    "--tag",
                    "v1.3.6",
                    "--notes-output",
                    str(root / "notes.md"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("does not match Cargo.toml", mismatch.stderr)

            packages = root / "packages"
            packages.mkdir()
            (packages / "oneroll-1.3.5-cp313t-cp313t-manylinux_x86_64.whl").touch()
            (packages / "oneroll-1.3.5.tar.gz").touch()
            free_threaded = subprocess.run(
                [
                    sys.executable,
                    str(RELEASE_CONTRACT),
                    "artifacts",
                    "--tag",
                    "v1.3.5",
                    "--directory",
                    str(packages),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(free_threaded.returncode, 0)
            self.assertIn("free-threaded", free_threaded.stderr)


if __name__ == "__main__":
    unittest.main()
