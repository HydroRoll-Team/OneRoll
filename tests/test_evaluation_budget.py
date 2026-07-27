import subprocess
import sys
import unittest

import oneroll


class EvaluationBudgetTests(unittest.TestCase):
    def test_unbounded_explosion_returns_budget_error(self):
        script = """
import oneroll

try:
    oneroll.roll("1d1!")
except ValueError as error:
    print(error)
    raise SystemExit(0 if "预算" in str(error) else 2)

raise SystemExit(3)
"""

        completed = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=2,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )

    def test_unbounded_reroll_until_returns_budget_error(self):
        with self.assertRaisesRegex(ValueError, "预算"):
            oneroll.roll("1d1R1")

    def test_roll_budget_is_shared_across_an_expression(self):
        with self.assertRaisesRegex(ValueError, "预算"):
            oneroll.roll("10000d1 + 1d1")

    def test_combined_reroll_modifiers_share_the_budget(self):
        with self.assertRaisesRegex(ValueError, "预算"):
            oneroll.roll("1d1ro1R1")

    def test_all_python_roll_entry_points_use_the_default_budget(self):
        roller = oneroll.OneRoll()
        roll_calls = [
            lambda: oneroll.roll_simple(10001, 1),
            lambda: roller.roll("1d1!"),
            lambda: roller.roll_simple(10001, 1),
            lambda: roller.roll_with_modifiers(1, 1, ["!"]),
        ]

        for roll_call in roll_calls:
            with self.subTest(roll_call=roll_call):
                with self.assertRaisesRegex(ValueError, "预算"):
                    roll_call()

    def test_cli_renders_budget_error_and_exits(self):
        completed = subprocess.run(
            [sys.executable, "-m", "oneroll", "1d1!"],
            capture_output=True,
            text=True,
            timeout=2,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("计算预算已耗尽", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
