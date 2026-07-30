import ast
import hashlib
import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
RFC = REPOSITORY_ROOT / "docs" / "rfcs" / "0004-python-engine-api-package-boundary.rst"
TARGET_STUB = REPOSITORY_ROOT / "docs" / "rfcs" / "0004-target-api.pyi"
MANIFEST = REPOSITORY_ROOT / "docs" / "rfcs" / "0004-api-contract.json"
RESULT_EXAMPLES = REPOSITORY_ROOT / "docs" / "rfcs" / "0003-examples.json"


class Rfc0004ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = ast.parse(TARGET_STUB.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.classes = {
            node.name: node
            for node in cls.module.body
            if isinstance(node, ast.ClassDef)
        }

    def test_rfc_embeds_checked_stub_and_manifest(self):
        content = RFC.read_text(encoding="utf-8")
        self.assertIn(".. literalinclude:: ../rfcs/0004-target-api.pyi", content)
        self.assertIn(".. literalinclude:: ../rfcs/0004-api-contract.json", content)

    def test_manifest_public_names_exist_in_target_stub(self):
        expected_classes = {
            self.manifest["primary_class"],
            *self.manifest["result_classes"],
            *self.manifest["support_classes"],
            *self.manifest["exception_bases"],
            *self.manifest["compatibility_classes"],
        }
        self.assertLessEqual(expected_classes, self.classes.keys())

        functions = {
            node.name for node in self.module.body if isinstance(node, ast.FunctionDef)
        }
        self.assertEqual(set(self.manifest["compatibility_functions"]), functions)

    def test_exception_hierarchy_matches_manifest(self):
        for name, expected_base in self.manifest["exception_bases"].items():
            with self.subTest(exception=name):
                bases = self.classes[name].bases
                self.assertEqual(len(bases), 1)
                self.assertIsInstance(bases[0], ast.Name)
                self.assertEqual(bases[0].id, expected_base)

    def test_engine_method_and_keyword_boundary_is_exact(self):
        engine = self.classes[self.manifest["primary_class"]]
        methods = {
            node.name: node for node in engine.body if isinstance(node, ast.FunctionDef)
        }
        self.assertEqual(
            set(methods) - {"__init__"}, set(self.manifest["engine_methods"])
        )

        expected = {
            "__init__": (["self"], ["resource_policy", "compatibility_mode"]),
            "parse": (["self", "source"], []),
            "validate": (["self", "source"], ["variables"]),
            "roll": (
                ["self", "expression"],
                ["variables", "seed", "cancellation", "timeout"],
            ),
            "run": (
                ["self", "program"],
                ["variables", "seed", "cancellation", "timeout"],
            ),
            "run_batch": (
                ["self", "program", "samples"],
                ["variables", "seed", "cancellation", "timeout"],
            ),
        }
        for name, (positional, keyword_only) in expected.items():
            with self.subTest(method=name):
                self.assertEqual(
                    [argument.arg for argument in methods[name].args.args], positional
                )
                self.assertEqual(
                    [argument.arg for argument in methods[name].args.kwonlyargs],
                    keyword_only,
                )

    def test_batch_manifest_and_examples_share_reference_vectors(self):
        examples = json.loads(RESULT_EXAMPLES.read_text(encoding="utf-8"))
        payload = examples["batch_cases"][0]["payload"]
        protocol = self.manifest["batch"]
        self.assertEqual(payload["random"]["algorithm"], protocol["algorithm"])
        self.assertEqual(protocol["execution_order"], "sequential")
        self.assertTrue(protocol["atomic"])

        root_seed = bytes.fromhex(payload["random"]["seed"])
        for index, result in enumerate(payload["results"]):
            derived = hashlib.sha256(
                b"OneRoll batch seed v1\0"
                + root_seed
                + index.to_bytes(8, byteorder="little")
            ).hexdigest()
            self.assertEqual(result["metadata"]["random"]["seed"], derived)

    def test_package_boundary_is_minimal_and_explicit(self):
        package = self.manifest["package"]
        self.assertEqual(package["core_dependencies"], [])
        self.assertEqual(package["extras"]["cli"], ["rich>=14.1.0"])
        self.assertEqual(package["extras"]["tui"], ["rich>=14.1.0", "textual>=6.1.0"])
        self.assertEqual(package["scripts"], ["oneroll", "1roll"])


if __name__ == "__main__":
    unittest.main()
