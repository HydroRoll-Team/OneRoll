import unittest
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).parents[1]
WORKFLOWS = REPOSITORY_ROOT / ".github" / "workflows"


def load_workflow(name: str) -> dict[str, object]:
    return yaml.load(
        (WORKFLOWS / name).read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def job_needs(job: dict[str, object]) -> set[str]:
    needs = job.get("needs", [])
    return {needs} if isinstance(needs, str) else set(needs)


class QualityGateContractTests(unittest.TestCase):
    def test_quality_workflow_runs_every_mandatory_gate(self):
        workflow = load_workflow("quality.yml")

        self.assertIn("workflow_call", workflow["on"])
        self.assertIn("pull_request", workflow["on"])
        self.assertIn("push", workflow["on"])
        steps = workflow["jobs"]["quality"]["steps"]
        commands = "\n".join(step.get("run", "") for step in steps)
        for command in (
            "cargo fmt --all -- --check",
            "cargo test --all-targets --all-features",
            "cargo test --release checked_i64_",
            "cargo clippy --all-targets --all-features -- -D warnings",
            "ruff check .",
            "ruff format --check .",
            "mypy --strict src/oneroll docs/rfcs/0004-target-api.pyi",
            "python -m unittest discover -s tests -v",
            "sphinx-build -W --keep-going -b html",
        ):
            with self.subTest(command=command):
                self.assertIn(command, commands)

    def test_delivery_workflows_cannot_bypass_quality(self):
        build = load_workflow("build.yml")
        docs = load_workflow("docs.yml")
        changelog = load_workflow("changelog.yml")

        for workflow in (build, docs, changelog):
            self.assertEqual(
                workflow["jobs"]["quality"]["uses"],
                "./.github/workflows/quality.yml",
            )

        for job_name in ("linux", "musllinux", "windows", "macos", "sdist"):
            with self.subTest(job=job_name):
                self.assertIn("quality", job_needs(build["jobs"][job_name]))

        self.assertIn("quality", job_needs(docs["jobs"]["build"]))
        self.assertNotIn("release", build["jobs"])
        self.assertIn("quality", job_needs(changelog["jobs"]["verify"]))
        self.assertIn("verify", job_needs(changelog["jobs"]["publish"]))

    def test_docs_deployment_uses_scoped_github_token(self):
        workflow = load_workflow("docs.yml")
        build = workflow["jobs"]["build"]
        self.assertEqual(build["permissions"]["contents"], "write")

        deploy = next(
            step for step in build["steps"] if step["name"] == "Deploy to GitHub Pages"
        )
        self.assertEqual(
            deploy["with"]["github_token"],
            "${{ secrets.GITHUB_TOKEN }}",
        )


if __name__ == "__main__":
    unittest.main()
