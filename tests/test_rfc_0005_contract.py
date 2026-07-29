import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
RFC = ROOT / "docs/rfcs/0005-verification-documentation-release.rst"
CORPUS_SCHEMA = ROOT / "docs/rfcs/0005-conformance.schema.json"
CORPUS_EXAMPLES = ROOT / "docs/rfcs/0005-conformance-examples.json"
RELEASE_CONTRACT = ROOT / "docs/rfcs/0005-release-contract.json"
RESULT_SCHEMA = ROOT / "docs/rfcs/0003-result.schema.json"
DOCS_INDEX = ROOT / "docs/source/index.rst"

FEATURE_FAMILIES = {
    "program",
    "instruction",
    "typed_value",
    "dice_source",
    "validator",
    "option",
    "function",
    "error",
}


class Rfc0005ContractTests(unittest.TestCase):
    def test_rfc_embeds_every_machine_checked_contract(self):
        rfc = RFC.read_text(encoding="utf-8")

        for filename in (
            CORPUS_SCHEMA.name,
            CORPUS_EXAMPLES.name,
            RELEASE_CONTRACT.name,
        ):
            with self.subTest(filename=filename):
                self.assertIn(f".. literalinclude:: ../rfcs/{filename}", rfc)

        self.assertIn("rfc-0005", DOCS_INDEX.read_text(encoding="utf-8"))

    def test_conformance_format_accepts_examples_and_covers_every_family(self):
        schema = json.loads(CORPUS_SCHEMA.read_text(encoding="utf-8"))
        examples = json.loads(CORPUS_EXAMPLES.read_text(encoding="utf-8"))
        result_schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
        registry = Registry().with_resource(
            result_schema["$id"], Resource.from_contents(result_schema)
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, registry=registry).validate(examples)

        cases = examples["cases"]
        case_ids = [case["id"] for case in cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))

        coverage = {
            family: {
                case["expect"]["outcome"]
                for case in cases
                if family in case["features"]
            }
            for family in FEATURE_FAMILIES
        }
        self.assertEqual(set(coverage), FEATURE_FAMILIES)
        for family, outcomes in coverage.items():
            with self.subTest(family=family):
                self.assertEqual(outcomes, {"success", "error"})

        for case in cases:
            with self.subTest(case=case["id"]):
                expectation = case["expect"]
                if expectation["outcome"] == "success":
                    self.assertIn("canonical", expectation)
                    self.assertIn("parse", expectation)
                    self.assertIn("value", expectation)
                    self.assertIn("scalar", expectation)
                    self.assertIn("trace", expectation)
                    self.assertIn("random", expectation)
                else:
                    self.assertIn("phase", expectation)
                    self.assertIn("code", expectation)
                    self.assertIn("span", expectation)

    def test_release_contract_freezes_explicit_milestone_publication(self):
        contract = json.loads(RELEASE_CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(contract["schema_version"], 1)
        self.assertEqual(contract["version_source"], "Cargo.toml:package.version")
        self.assertEqual(contract["tag_template"], "v{cargo_version}")
        self.assertEqual(contract["release_branch"], "main")

        approval = contract["publication_approval"]
        self.assertTrue(approval["explicit"])
        self.assertEqual(approval["event"], "workflow_dispatch")
        self.assertEqual(approval["environment"], "pypi")
        self.assertTrue(approval["required_reviewers"])
        self.assertEqual(approval["credential"], "pypi-trusted-publisher-oidc")

        milestones = contract["milestone_releases"]
        self.assertEqual(
            [release["milestone"] for release in milestones],
            ["M0", "M1", "M2", "M3", "M4", "M5", "M6"],
        )
        self.assertEqual(
            [release["cargo_version"] for release in milestones],
            [
                "1.3.5",
                "2.0.0-alpha.0",
                "2.0.0-alpha.1",
                "2.0.0-beta.1",
                "2.0.0-rc.1",
                "2.0.0",
                "2.1.0",
            ],
        )
        self.assertEqual(
            [release["python_version"] for release in milestones],
            ["1.3.5", "2.0.0a0", "2.0.0a1", "2.0.0b1", "2.0.0rc1", "2.0.0", "2.1.0"],
        )
        self.assertFalse(milestones[1]["publish_pypi"])
        self.assertTrue(all(item["github_release"] for item in milestones))

        evidence_ids = {item["id"] for item in contract["required_evidence"]}
        self.assertEqual(
            evidence_ids,
            {
                "source",
                "quality",
                "conformance",
                "fuzz_property",
                "docs",
                "wheel_smoke",
                "provenance",
                "sbom_audit",
                "release_notes",
            },
        )


if __name__ == "__main__":
    unittest.main()
