import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class FuzzGateContractTests(unittest.TestCase):
    def test_scheduled_fuzz_targets_have_time_and_memory_boundaries(self):
        workflow = (ROOT / ".github/workflows/fuzz.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("parse_program", workflow)
        self.assertIn("evaluate_program", workflow)
        self.assertIn("-max_total_time=120", workflow)
        self.assertIn("-timeout=5", workflow)
        self.assertIn("-rss_limit_mb=2048", workflow)
        self.assertIn("if: failure()", workflow)

    def test_fuzz_targets_and_regression_corpora_are_versioned(self):
        required = [
            "fuzz/Cargo.toml",
            "fuzz/fuzz_targets/parse_program.rs",
            "fuzz/fuzz_targets/evaluate_program.rs",
            "fuzz/corpus/parse_program/empty-instruction",
            "fuzz/corpus/parse_program/deep-parentheses",
            "fuzz/corpus/evaluate_program/infinite-explode",
            "fuzz/corpus/evaluate_program/infinite-reroll",
            "fuzz/corpus/evaluate_program/arithmetic-overflow",
        ]

        for relative_path in required:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

        for target in ("parse_program", "evaluate_program"):
            source = (ROOT / f"fuzz/fuzz_targets/{target}.rs").read_text(
                encoding="utf-8"
            )
            self.assertIn("MAX_INPUT_BYTES", source)
            self.assertIn("ResourcePolicy::default()", source)

    def test_property_suite_is_a_release_quality_gate(self):
        quality = (ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8")
        properties = (ROOT / "src/property_tests.rs").read_text(encoding="utf-8")

        self.assertIn("cargo test --release property_", quality)
        self.assertIn("property_numeric_dice_stay_in_range", properties)
        self.assertIn("property_equal_seeded_requests_replay_exactly", properties)
        self.assertIn("property_relaxing_generated_value_budget", properties)
        self.assertIn("property_modifier_combinations_terminate", properties)


if __name__ == "__main__":
    unittest.main()
