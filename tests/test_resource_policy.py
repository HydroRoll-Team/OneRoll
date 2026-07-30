import unittest

import oneroll


class ResourcePolicyTests(unittest.TestCase):
    def test_python_users_can_inspect_defaults_and_hard_maximums(self):
        policy = oneroll.ResourcePolicy()

        self.assertEqual(policy.limits()["source_bytes"], 65_536)
        self.assertEqual(policy.hard_limits()["source_bytes"], 1_048_576)

    def test_python_users_cannot_exceed_a_hard_maximum(self):
        with self.assertRaisesRegex(ValueError, r"\[policy\.limit_above_hard_max\]"):
            oneroll.ResourcePolicy().with_limit("source_bytes", 1_048_577)

    def test_python_users_cannot_configure_a_negative_limit(self):
        with self.assertRaisesRegex(ValueError, r"\[policy\.invalid_limit\]"):
            oneroll.ResourcePolicy().with_limit("source_bytes", -1)

    def test_python_users_can_lower_the_source_byte_limit(self):
        accepted = oneroll.OneRoll(
            oneroll.ResourcePolicy().with_limit("source_bytes", 3)
        )
        rejected = oneroll.OneRoll(
            oneroll.ResourcePolicy().with_limit("source_bytes", 2)
        )

        self.assertGreaterEqual(accepted.roll("1d6")["total"], 1)
        with self.assertRaisesRegex(ValueError, r"\[limit\.source_bytes\]"):
            rejected.roll("1d6")

    def test_parse_depth_accepts_the_boundary_and_rejects_the_next_level(self):
        policy = oneroll.ResourcePolicy().with_limit("parse_depth", 2)
        roller = oneroll.OneRoll(policy)

        self.assertEqual(roller.roll("((1))")["total"], 1)
        with self.assertRaisesRegex(ValueError, r"\[limit\.parse_depth\]"):
            roller.roll("(((1)))")

    def test_parsed_instruction_limit_is_shared_across_semicolons(self):
        policy = oneroll.ResourcePolicy().with_limit("parsed_instructions", 2)
        roller = oneroll.OneRoll(policy)

        self.assertEqual(len(roller.run("1;2")["results"]), 2)
        with self.assertRaisesRegex(ValueError, r"\[limit\.parsed_instructions\]"):
            roller.run("1;2;3")

    def test_ast_node_limit_counts_the_whole_program(self):
        policy = oneroll.ResourcePolicy().with_limit("ast_nodes", 5)
        roller = oneroll.OneRoll(policy)

        self.assertEqual(len(roller.run("1;2")["results"]), 2)
        with self.assertRaisesRegex(ValueError, r"\[limit\.ast_nodes\]"):
            roller.run("1;2;3")

    def test_ast_node_limit_counts_the_legacy_comment_wrapper(self):
        roller = oneroll.OneRoll(oneroll.ResourcePolicy().with_limit("ast_nodes", 3))

        self.assertEqual(roller.roll("1")["total"], 1)
        with self.assertRaisesRegex(ValueError, r"\[limit\.ast_nodes\]"):
            roller.roll("1 # comment")

    def test_source_item_limit_applies_to_convenience_methods(self):
        policy = oneroll.ResourcePolicy().with_limit("source_items", 2)
        roller = oneroll.OneRoll(policy)

        self.assertGreaterEqual(roller.roll_simple(2, 6), 2)
        with self.assertRaisesRegex(ValueError, r"\[limit\.source_items\]"):
            roller.roll_simple(3, 6)

    def test_generated_value_limit_does_not_reset_at_semicolons(self):
        policy = oneroll.ResourcePolicy().with_limit("generated_values", 2)
        roller = oneroll.OneRoll(policy)

        self.assertEqual(len(roller.run("1d1;1d1")["results"]), 2)
        with self.assertRaisesRegex(ValueError, r"\[limit\.generated_values\]"):
            roller.run("1d1;1d1;1d1")

    def test_batch_samples_are_checked_before_the_batch_runs(self):
        policy = oneroll.ResourcePolicy().with_limit("batch_samples", 2)
        roller = oneroll.OneRoll(policy)

        self.assertEqual(len(roller.roll_multiple("1d1", 2)), 2)
        with self.assertRaisesRegex(ValueError, r"\[limit\.batch_samples\]"):
            roller.roll_multiple("1d1", 3)

    def test_generated_value_limit_is_shared_by_all_batch_samples(self):
        policy = oneroll.ResourcePolicy().with_limit("generated_values", 2)
        roller = oneroll.OneRoll(policy)

        self.assertEqual(len(roller.roll_multiple("1d1", 2)), 2)
        with self.assertRaisesRegex(ValueError, r"\[limit\.generated_values\]"):
            roller.roll_multiple("1d1", 3)

    def test_execution_limits_have_exact_boundaries(self):
        cases = [
            ("executed_instructions", "1", "1;2"),
            ("nesting_depth", "1", "(1)"),
            ("rng_words", "1d1", "2d1"),
            ("collection_items", "1d1", "2d1"),
        ]

        for resource, accepted, rejected in cases:
            with self.subTest(resource=resource):
                policy = oneroll.ResourcePolicy().with_limit(resource, 1)
                roller = oneroll.OneRoll(policy)
                roller.run(accepted)
                with self.assertRaisesRegex(ValueError, rf"\[limit\.{resource}\]"):
                    roller.run(rejected)

    def test_work_units_charge_instruction_activation_and_ast_evaluation(self):
        accepted = oneroll.OneRoll(oneroll.ResourcePolicy().with_limit("work_units", 2))
        rejected = oneroll.OneRoll(oneroll.ResourcePolicy().with_limit("work_units", 1))

        self.assertEqual(accepted.roll("1")["total"], 1)
        with self.assertRaisesRegex(ValueError, r"\[limit\.work_units\]"):
            rejected.roll("1")

    def test_output_item_limit_counts_result_roots_and_values(self):
        accepted = oneroll.OneRoll(
            oneroll.ResourcePolicy().with_limit("output_items", 2)
        )
        rejected = oneroll.OneRoll(
            oneroll.ResourcePolicy().with_limit("output_items", 1)
        )

        self.assertEqual(accepted.roll("1d1")["total"], 1)
        with self.assertRaisesRegex(ValueError, r"\[limit\.output_items\]"):
            rejected.roll("1d1")

    def test_output_byte_limit_is_enforced(self):
        roller = oneroll.OneRoll(oneroll.ResourcePolicy().with_limit("output_bytes", 0))

        with self.assertRaisesRegex(ValueError, r"\[limit\.output_bytes\]"):
            roller.roll("1")

    def test_convenience_methods_charge_their_external_output_shape(self):
        one_byte = oneroll.OneRoll(
            oneroll.ResourcePolicy().with_limit("output_bytes", 1)
        )
        five_bytes = oneroll.OneRoll(
            oneroll.ResourcePolicy().with_limit("output_bytes", 5)
        )

        self.assertEqual(one_byte.roll_simple(1, 1), 1)
        with self.assertRaisesRegex(ValueError, r"\[limit\.output_bytes\]"):
            five_bytes.roll_with_modifiers(1, 1, [])

    def test_batches_reject_non_positive_sample_counts(self):
        with self.assertRaisesRegex(ValueError, r"\[input\.invalid_batch_samples\]"):
            oneroll.roll_multiple("1d1", 0)

    def test_free_batch_convenience_functions_use_the_default_policy(self):
        for operation in (
            lambda: oneroll.roll_multiple("1d1", 10_001),
            lambda: oneroll.roll_statistics("1d1", 10_001),
        ):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(ValueError, r"\[limit\.batch_samples\]"):
                    operation()


if __name__ == "__main__":
    unittest.main()
