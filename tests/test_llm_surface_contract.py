from __future__ import annotations

import json
import re
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = REPOSITORY_ROOT / "benchmarks" / "llm_surface" / "cases.json"
SCHEMA_PATH = REPOSITORY_ROOT / "benchmarks" / "llm_surface" / "cases.schema.json"
RFC_PATH = REPOSITORY_ROOT / "docs" / "rfcs" / "0001-dice-program-language-v2.rst"

CANONICAL_SPACING_PATTERNS = (
    re.compile(r",\S"),
    re.compile(r'(?<=[0-9}\])"])(?:\*\*|[+\-*/])'),
    re.compile(r'(?<=[0-9}\])"] )(?:\*\*|[+\-*/])(?=\S)'),
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def syntax_without_strings_or_comment(canonical: str) -> str:
    syntax: list[str] = []
    in_string = False
    escaped = False
    delimiter_depth = 0

    for character in canonical:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
                syntax.append(character)
            continue

        if character == '"':
            in_string = True
            syntax.append(character)
        elif character == "#" and delimiter_depth == 0:
            break
        else:
            syntax.append(character)
            if character in "([{":
                delimiter_depth += 1
            elif character in ")]}" and delimiter_depth > 0:
                delimiter_depth -= 1

    return "".join(syntax)


class LlmSurfaceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = load_json(SCHEMA_PATH)
        self.corpus = load_json(CORPUS_PATH)
        self.cases = self.corpus["cases"]

    def test_schema_is_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(self.schema)

    def test_corpus_matches_schema(self) -> None:
        errors = sorted(
            Draft202012Validator(self.schema).iter_errors(self.corpus),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual(
            errors,
            [],
            "\n".join(
                f"{list(error.absolute_path)}: {error.message}" for error in errors
            ),
        )

    def test_case_ids_are_unique(self) -> None:
        counts = Counter(case["id"] for case in self.cases)
        duplicate_ids = sorted(
            case_id for case_id, count in counts.items() if count > 1
        )
        self.assertEqual(duplicate_ids, [], f"duplicate case IDs: {duplicate_ids}")

    def test_initial_corpus_has_broad_surface_coverage(self) -> None:
        self.assertGreaterEqual(len(self.cases), 32)

    def test_each_intent_has_matching_en_and_zh_cases(self) -> None:
        cases_by_intent = defaultdict(list)
        for case in self.cases:
            cases_by_intent[case["intent_id"]].append(case)

        expected_locale_counts = Counter({"en": 1, "zh-CN": 1})
        for intent_id, paired_cases in cases_by_intent.items():
            locale_counts = Counter(case["locale"] for case in paired_cases)
            self.assertEqual(locale_counts, expected_locale_counts, intent_id)

            by_locale = {case["locale"]: case for case in paired_cases}
            english = by_locale["en"]
            chinese = by_locale["zh-CN"]
            self.assertEqual(english["id"], f"{intent_id}.en")
            self.assertEqual(chinese["id"], f"{intent_id}.zh-CN")
            self.assertEqual(english["expected"], chinese["expected"], intent_id)
            self.assertEqual(
                english["feature_tags"], chinese["feature_tags"], intent_id
            )
            self.assertEqual(
                english["rfc_reference"], chinese["rfc_reference"], intent_id
            )

    def test_canonical_expressions_are_single_clean_values(self) -> None:
        for case in self.cases:
            canonical = case["expected"]["canonical"]
            with self.subTest(case_id=case["id"]):
                self.assertTrue(canonical)
                self.assertEqual(canonical, canonical.strip())
                self.assertNotIn("```", canonical)
                self.assertNotIn("\r", canonical)
                syntax = syntax_without_strings_or_comment(canonical)
                for pattern in CANONICAL_SPACING_PATTERNS:
                    self.assertNotRegex(syntax, pattern)

    def test_canonical_spacing_ignores_literal_and_comment_text(self) -> None:
        valid_canonical_values = (
            '1L["a,b", "1+2"]',
            "1d6 # keep,a+b",
        )
        for canonical in valid_canonical_values:
            syntax = syntax_without_strings_or_comment(canonical)
            for pattern in CANONICAL_SPACING_PATTERNS:
                self.assertNotRegex(syntax, pattern, canonical)

    def test_rfc_references_are_present_in_rfc_0001(self) -> None:
        rfc_text = RFC_PATH.read_text(encoding="utf-8")
        for case in self.cases:
            with self.subTest(case_id=case["id"]):
                self.assertIn(case["rfc_reference"], rfc_text)

    def test_feature_tags_cover_multiple_surface_families(self) -> None:
        required_families = {
            "dice",
            "validator",
            "option",
            "conditional",
            "function",
            "program",
            "list",
            "collection",
        }
        observed_families = {
            tag.partition(".")[0] for case in self.cases for tag in case["feature_tags"]
        }
        self.assertTrue(
            required_families <= observed_families,
            f"missing feature families: {sorted(required_families - observed_families)}",
        )


if __name__ == "__main__":
    unittest.main()
