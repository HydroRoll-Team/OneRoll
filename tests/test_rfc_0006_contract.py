import json
import unittest
from fractions import Fraction
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
RFC = ROOT / "docs/rfcs/0006-program-sampling-exact-analysis.rst"
MATRIX = ROOT / "docs/rfcs/0006-capability-matrix.json"
DISTRIBUTIONS = ROOT / "docs/rfcs/0006-distributions.json"
ANALYSIS_CONTRACT = ROOT / "docs/rfcs/0006-analysis-contract.json"
RESULT_SCHEMA = ROOT / "docs/rfcs/0003-result.schema.json"
DOCS_INDEX = ROOT / "docs/source/index.rst"

REQUIRED_MATRIX_IDS = {
    "program.single_instruction",
    "program.multiple_instructions",
    "value.scalar",
    "value.text",
    "value.boolean",
    "value.values",
    "value.roll_set",
    "variable.deterministic",
    "variable.probabilistic",
    "dice.numeric",
    "dice.range",
    "dice.list_weighted",
    "dice.unique_numeric",
    "dice.unique_list",
    "validator.pure",
    "arithmetic.add_subtract_multiply",
    "arithmetic.divide",
    "arithmetic.exponent",
    "option.keep_drop",
    "option.filter_sort_count",
    "option.occurrences",
    "option.unique",
    "option.paint_split_group",
    "option.reroll_once",
    "option.source_generating",
    "option.merge",
    "option.bind",
    "function.repeat",
    "control.conditional",
    "node.backward_jump",
    "command.cli_only",
    "comment",
}


class Rfc0006ContractTests(unittest.TestCase):
    def test_rfc_embeds_every_machine_checked_contract(self):
        rfc = RFC.read_text(encoding="utf-8")

        for filename in (MATRIX.name, DISTRIBUTIONS.name, ANALYSIS_CONTRACT.name):
            with self.subTest(filename=filename):
                self.assertIn(f".. literalinclude:: ../rfcs/{filename}", rfc)

        self.assertIn("rfc-0006", DOCS_INDEX.read_text(encoding="utf-8"))

    def test_capability_matrix_is_complete_and_never_falls_back(self):
        matrix = json.loads(MATRIX.read_text(encoding="utf-8"))

        self.assertEqual(matrix["schema_version"], 1)
        self.assertEqual(matrix["analysis_schema_version"], "1.0")
        self.assertEqual(matrix["decision_status"], "provisional")
        self.assertEqual(matrix["exact_fallback"], "never")

        entries = matrix["constructs"]
        by_id = {entry["id"]: entry for entry in entries}
        self.assertEqual(len(by_id), len(entries))
        self.assertEqual(set(by_id), REQUIRED_MATRIX_IDS)

        for entry in entries:
            with self.subTest(construct=entry["id"]):
                self.assertIn(entry["status"], {"supported", "bounded", "unsupported"})
                self.assertTrue(entry["reason"])
                self.assertRegex(entry["tracking_issue"], r"^#\d+$")
                if entry["status"] == "bounded":
                    self.assertTrue(entry["limits"])
                if entry["status"] == "unsupported":
                    expected_error = (
                        "analysis.unsupported.program_arity"
                        if entry["id"] == "program.multiple_instructions"
                        else "analysis.unsupported_construct"
                    )
                    self.assertEqual(entry["error_code"], expected_error)

        self.assertEqual(
            by_id["program.multiple_instructions"]["status"], "unsupported"
        )
        self.assertEqual(by_id["variable.deterministic"]["status"], "supported")
        self.assertEqual(by_id["variable.probabilistic"]["status"], "unsupported")
        self.assertEqual(by_id["dice.unique_list"]["status"], "bounded")
        self.assertEqual(by_id["option.source_generating"]["status"], "unsupported")
        self.assertEqual(by_id["function.repeat"]["status"], "bounded")
        self.assertEqual(by_id["control.conditional"]["status"], "bounded")
        self.assertEqual(by_id["option.bind"]["status"], "unsupported")
        self.assertEqual(by_id["node.backward_jump"]["status"], "unsupported")

    def test_analysis_api_separates_sampling_from_exact_execution(self):
        contract = json.loads(ANALYSIS_CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(contract["schema_version"], 1)
        self.assertEqual(contract["analysis_schema_version"], "1.0")
        self.assertEqual(contract["status"], "draft")
        self.assertEqual(contract["methods"], ["sample", "analyze_exact"])
        self.assertEqual(contract["exact"]["fallback"], "never")
        self.assertFalse(contract["exact"]["accepts_seed"])
        self.assertEqual(contract["exact"]["max_program_instructions"], 1)
        self.assertEqual(contract["exact"]["outcome_value"], "analysis-value")
        self.assertEqual(
            contract["exact"]["possible_runtime_errors"],
            "reject-atomically-without-distribution",
        )

        sampling = contract["sampling"]
        self.assertEqual(sampling["execution"], "Engine.run_batch")
        self.assertEqual(sampling["random_algorithm"], "oneroll-chacha12-v1")
        self.assertEqual(sampling["batch_algorithm"], "oneroll-sha256-batch-v1")
        self.assertTrue(sampling["atomic"])
        self.assertEqual(sampling["histogram_key"], "canonical-analysis-value-json")
        self.assertEqual(
            sampling["quantiles"],
            {"method": "nearest-rank", "probabilities": [0.05, 0.25, 0.5, 0.75, 0.95]},
        )
        self.assertEqual(
            sampling["confidence"],
            {
                "method": "wilson-score",
                "level": 0.95,
                "z": 1.959963984540054,
            },
        )
        self.assertEqual(
            set(sampling["summary_fields"]),
            {
                "count",
                "min",
                "max",
                "mean",
                "variance",
                "standard_error",
                "quantiles",
                "histogram",
            },
        )

        limits = contract["exact"]["limits"]
        self.assertEqual(
            set(limits),
            {
                "analysis_states",
                "analysis_support",
                "analysis_operations",
                "analysis_bytes",
                "analysis_rational_bits",
            },
        )
        for name, values in limits.items():
            with self.subTest(limit=name):
                self.assertGreater(values["default"], 0)
                self.assertGreaterEqual(values["hard_maximum"], values["default"])

        self.assertEqual(
            set(contract["error_codes"]),
            {
                "analysis.unsupported_construct",
                "analysis.unsupported.program_arity",
                "analysis.possible_runtime_error",
                "analysis.state_limit",
                "analysis.support_limit",
                "analysis.operation_limit",
                "analysis.byte_limit",
                "analysis.rational_limit",
                "analysis.cancelled",
                "analysis.deadline_exceeded",
            },
        )
        self.assertTrue(contract["cancellation"]["atomic"])
        self.assertEqual(contract["cancellation"]["partial_result"], "never")

    def test_analysis_values_reuse_result_value_primitives(self):
        result_schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
        contract = json.loads(ANALYSIS_CONTRACT.read_text(encoding="utf-8"))
        analysis_schema = contract["analysis_value_schema"]

        for definition in ("ScalarValue", "TextValue", "BooleanValue"):
            with self.subTest(definition=definition):
                self.assertEqual(
                    analysis_schema["$defs"][definition],
                    result_schema["$defs"][definition],
                )

        self.assertEqual(
            analysis_schema["$defs"]["RollSetValue"]["properties"]["item_kind"],
            result_schema["$defs"]["RollSetValue"]["properties"]["item_kind"],
        )
        value_kinds = {
            analysis_schema["$defs"][name]["properties"]["kind"]["const"]
            for name in (
                "ScalarValue",
                "TextValue",
                "BooleanValue",
                "ValuesValue",
                "RollSetValue",
            )
        }
        self.assertEqual(value_kinds, set(contract["value_kinds"]))

    def test_normative_exact_distributions_are_typed_and_sum_to_one(self):
        payload = json.loads(DISTRIBUTIONS.read_text(encoding="utf-8"))
        contract = json.loads(ANALYSIS_CONTRACT.read_text(encoding="utf-8"))
        value_schema = contract["analysis_value_schema"]
        Draft202012Validator.check_schema(value_schema)
        value_validator = Draft202012Validator(value_schema)

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["analysis_schema_version"], "1.0")
        cases = payload["cases"]
        by_id = {case["id"]: case for case in cases}
        self.assertEqual(len(by_id), len(cases))
        self.assertEqual(
            set(by_id),
            {
                "numeric.2d2",
                "option.keep_high_2d2",
                "list.weighted_single",
                "list.weighted_unique_ordered",
            },
        )

        for case in cases:
            with self.subTest(case=case["id"]):
                probability_sum = Fraction(0, 1)
                value_keys = set()
                for outcome in case["outcomes"]:
                    value_validator.validate(outcome["value"])
                    probability = Fraction(
                        int(outcome["probability"]["numerator"]),
                        int(outcome["probability"]["denominator"]),
                    )
                    self.assertGreater(probability, 0)
                    probability_sum += probability
                    value_key = json.dumps(
                        outcome["value"], sort_keys=True, separators=(",", ":")
                    )
                    self.assertNotIn(value_key, value_keys)
                    value_keys.add(value_key)
                self.assertEqual(probability_sum, Fraction(1, 1))

        def scalar_probabilities(case_id: str) -> dict[int, Fraction]:
            probabilities: dict[int, Fraction] = {}
            for outcome in by_id[case_id]["outcomes"]:
                scalar = outcome["scalar"]
                self.assertIsInstance(scalar, int)
                probability = Fraction(
                    int(outcome["probability"]["numerator"]),
                    int(outcome["probability"]["denominator"]),
                )
                probabilities[scalar] = (
                    probabilities.get(scalar, Fraction()) + probability
                )
            return probabilities

        self.assertEqual(
            scalar_probabilities("numeric.2d2"),
            {2: Fraction(1, 4), 3: Fraction(1, 2), 4: Fraction(1, 4)},
        )
        self.assertEqual(
            scalar_probabilities("option.keep_high_2d2"),
            {1: Fraction(1, 4), 2: Fraction(3, 4)},
        )

        unique = {
            tuple(
                item["value"]["value"] for item in outcome["value"]["items"]
            ): Fraction(
                int(outcome["probability"]["numerator"]),
                int(outcome["probability"]["denominator"]),
            )
            for outcome in by_id["list.weighted_unique_ordered"]["outcomes"]
        }
        self.assertEqual(
            unique,
            {
                ("A", "B"): Fraction(1, 4),
                ("A", "C"): Fraction(1, 4),
                ("B", "A"): Fraction(1, 6),
                ("B", "C"): Fraction(1, 12),
                ("C", "A"): Fraction(1, 6),
                ("C", "B"): Fraction(1, 12),
            },
        )


if __name__ == "__main__":
    unittest.main()
