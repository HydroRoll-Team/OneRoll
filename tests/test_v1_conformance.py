import json
import unittest
from pathlib import Path

import oneroll


CORPUS_PATH = Path(__file__).parent / "conformance" / "v1.json"
CLASSIFICATIONS = {"intended", "known_defect", "compatibility_sensitive"}


class V1ConformanceTests(unittest.TestCase):
    def test_corpus_contract_is_machine_readable(self):
        corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

        self.assertEqual(corpus["schema_version"], 1)
        self.assertEqual(corpus["language"], "oneroll-v1")
        self.assertTrue(corpus["cases"])
        self.assertTrue(corpus["program_cases"])
        self.assertEqual(
            set(corpus), {"schema_version", "language", "cases", "program_cases"}
        )

        all_cases = corpus["cases"] + corpus["program_cases"]
        case_ids = [case["id"] for case in all_cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        for case in all_cases:
            self.assertEqual(
                set(case),
                {"id", "expression", "classification", "note", "expect"}
                | (
                    {"tracking_issue"}
                    if case["classification"] != "intended"
                    else set()
                ),
                case["id"],
            )
            self.assertTrue(case["id"])
            self.assertIsInstance(case["expression"], str)
            self.assertTrue(case["note"])
            self.assertIn(case["classification"], CLASSIFICATIONS)
            self.assertIn(case["expect"]["status"], {"success", "error"})
            if case["classification"] != "intended":
                self.assertRegex(case["tracking_issue"], r"^#\d+$")

            if case["expect"]["status"] == "success":
                self.assertEqual(
                    set(case["expect"]),
                    {
                        "status",
                        "totals" if case in corpus["program_cases"] else "total",
                        "flattened_rolls",
                        "comment",
                    },
                    case["id"],
                )
            else:
                self.assertEqual(
                    set(case["expect"]),
                    {"status", "message_contains"},
                    case["id"],
                )

    def test_installed_python_package_matches_corpus(self):
        corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

        for case in corpus["cases"]:
            with self.subTest(
                case=case["id"],
                classification=case["classification"],
                expression=case["expression"],
            ):
                expected = case["expect"]
                if expected["status"] == "error":
                    with self.assertRaisesRegex(
                        ValueError, expected["message_contains"]
                    ):
                        oneroll.roll(case["expression"])
                    continue

                result = oneroll.roll(case["expression"])
                flattened_rolls = sum(len(group) for group in result["rolls"])
                self.assertEqual(result["total"], expected["total"])
                self.assertEqual(flattened_rolls, expected["flattened_rolls"])
                self.assertEqual(result["comment"], expected["comment"])

    def test_installed_python_program_api_matches_corpus(self):
        corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

        for case in corpus["program_cases"]:
            with self.subTest(
                case=case["id"],
                classification=case["classification"],
                program=case["expression"],
            ):
                expected = case["expect"]
                if expected["status"] == "error":
                    with self.assertRaisesRegex(
                        ValueError, expected["message_contains"]
                    ):
                        oneroll.run(case["expression"])
                    continue

                result = oneroll.run(case["expression"])
                flattened_rolls = sum(
                    len(group)
                    for instruction in result["results"]
                    for group in instruction["rolls"]
                )
                self.assertEqual(
                    [instruction["total"] for instruction in result["results"]],
                    expected["totals"],
                )
                self.assertEqual(flattened_rolls, expected["flattened_rolls"])
                self.assertEqual(result["comment"], expected["comment"])


if __name__ == "__main__":
    unittest.main()
