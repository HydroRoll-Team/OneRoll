import json
import subprocess
import sys
import unittest
from pathlib import Path

import oneroll
from jsonschema import Draft202012Validator


ROOT = Path(__file__).parents[1]
SCHEMA = json.loads(
    (ROOT / "docs/rfcs/0003-result.schema.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA)


class StructuredErrorTests(unittest.TestCase):
    def assert_valid_envelope(self, error: oneroll.OneRollError):
        envelope = error.to_envelope()
        VALIDATOR.validate(envelope)
        self.assertEqual(envelope["schema_version"], "2.0")
        self.assertEqual(envelope["kind"], "error")
        self.assertNotIn("instructions", envelope)
        self.assertNotIn("roll_nodes", envelope)
        self.assertNotIn("trace_nodes", envelope)
        return envelope

    def test_parse_error_has_utf8_byte_span_and_expected_constructs(self):
        with self.assertRaises(oneroll.ParseError) as caught:
            oneroll.roll("🎲")

        error = caught.exception
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.phase, "parse")
        self.assertEqual(error.code, "parse.invalid_syntax")
        self.assertEqual(error.span.to_dict(), {"start_byte": 0, "end_byte": 4})
        self.assertTrue(error.expected)
        self.assertEqual(error.to_dict()["span"], error.span.to_dict())
        self.assert_valid_envelope(error)

    def test_resource_error_has_complete_counters_and_replay_metadata(self):
        roller = oneroll.OneRoll(
            oneroll.ResourcePolicy().with_limit("generated_values", 1)
        )

        with self.assertRaises(oneroll.ResourceLimitError) as caught:
            roller.run("1d1;1d1")

        error = caught.exception
        self.assertEqual(error.phase, "evaluate")
        self.assertEqual(error.code, "limit.generated_values")
        self.assertEqual(error.resource, "generated_values")
        self.assertEqual((error.used, error.requested, error.limit), (1, 1, 1))
        self.assertEqual(error.span.to_dict(), {"start_byte": 0, "end_byte": 7})
        self.assertEqual(error.random.algorithm, "oneroll-chacha12-v1")
        self.assertEqual(error.random.rng_words, 2)
        self.assertEqual(len(error.random.seed), 64)
        self.assert_valid_envelope(error)

    def test_arithmetic_and_policy_failures_use_specific_subclasses(self):
        with self.assertRaises(oneroll.ArithmeticEvaluationError) as arithmetic:
            oneroll.roll("1 / 0")
        self.assertEqual(arithmetic.exception.phase, "evaluate")
        self.assertEqual(arithmetic.exception.code, "arithmetic.divide_by_zero")
        self.assertEqual(
            arithmetic.exception.span.to_dict(), {"start_byte": 0, "end_byte": 5}
        )
        self.assert_valid_envelope(arithmetic.exception)

        with self.assertRaises(oneroll.ValidationError) as policy:
            oneroll.ResourcePolicy().with_limit("source_bytes", -1)
        self.assertEqual(policy.exception.phase, "validate")
        self.assertEqual(policy.exception.code, "policy.invalid_limit")
        self.assert_valid_envelope(policy.exception)

    def test_core_value_error_retains_machine_readable_envelope(self):
        with self.assertRaises(ValueError) as caught:
            oneroll._core.roll_dice("+")

        encoded = caught.exception._oneroll_error_json
        VALIDATOR.validate(json.loads(encoded))

    def test_every_compatibility_entry_point_raises_structured_errors(self):
        roller = oneroll.OneRoll()
        operations = (
            lambda: oneroll.roll("+"),
            lambda: oneroll.run("+"),
            lambda: roller.roll("+"),
            lambda: roller.run("+"),
            lambda: roller.roll_multiple("+", 1),
            lambda: roller.roll_simple(0, 6),
            lambda: roller.roll_with_modifiers(1, 6, ["unknown"]),
            lambda: oneroll.roll_multiple("+", 1),
            lambda: oneroll.roll_statistics("+", 1),
        )

        for operation in operations:
            with (
                self.subTest(operation=operation),
                self.assertRaises(oneroll.OneRollError) as caught,
            ):
                operation()
            self.assert_valid_envelope(caught.exception)

    def test_cli_json_failure_is_exact_rfc_0003_envelope(self):
        completed = subprocess.run(
            [sys.executable, "-m", "oneroll", "--json", "1 / 0"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        payload = json.loads(completed.stdout)
        VALIDATOR.validate(payload)
        self.assertEqual(payload["error"]["phase"], "evaluate")
        self.assertEqual(payload["error"]["code"], "arithmetic.divide_by_zero")
        self.assertEqual(completed.stderr, "")

    def test_cli_json_policy_failure_is_structured_before_execution(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "oneroll",
                "--json",
                "--limit",
                "source_bytes=-1",
                "1d6",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(completed.returncode, 2, completed.stderr)
        payload = json.loads(completed.stdout)
        VALIDATOR.validate(payload)
        self.assertEqual(payload["error"]["phase"], "validate")
        self.assertEqual(payload["error"]["code"], "policy.invalid_limit")

    def test_cli_json_stats_failure_has_no_progress_output(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "oneroll",
                "--json",
                "--stats",
                "1d1",
                "--times",
                "0",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        payload = json.loads(completed.stdout)
        VALIDATOR.validate(payload)
        self.assertEqual(payload["error"]["code"], "input.invalid_batch_samples")


if __name__ == "__main__":
    unittest.main()
