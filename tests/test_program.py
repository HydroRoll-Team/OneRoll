import subprocess
import sys
import unittest

import oneroll


class ProgramExecutionTests(unittest.TestCase):
    def test_python_run_executes_each_instruction_in_order(self):
        result = oneroll.run("1; 2 # setup")

        self.assertEqual([item["total"] for item in result["results"]], [1, 2])
        self.assertEqual(result["comment"], "setup")

    def test_cli_renders_each_instruction_and_program_comment(self):
        completed = subprocess.run(
            [sys.executable, "-m", "oneroll", "1; 2 # setup"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout.count("总点数"), 2)
        self.assertIn("setup", completed.stdout)

    def test_program_instructions_share_one_evaluation_budget(self):
        with self.assertRaisesRegex(ValueError, "计算预算已耗尽"):
            oneroll.run("10000d1; 1d1")

    def test_program_rejects_more_than_the_default_instruction_limit(self):
        program = ";".join(["1"] * 1001)

        with self.assertRaisesRegex(ValueError, "程序指令数量超过限制"):
            oneroll.run(program)

    def test_program_rejects_empty_instructions(self):
        for program in (";1", "1;", "1;;2"):
            with self.subTest(program=program), self.assertRaises(ValueError):
                oneroll.run(program)

    def test_program_comment_cannot_consume_a_following_line(self):
        with self.assertRaises(ValueError):
            oneroll.run("1 # first line\n2")

    def test_roll_keeps_single_expression_comment_compatibility(self):
        result = oneroll.roll("1 # legacy")

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["comment"], "legacy")


if __name__ == "__main__":
    unittest.main()
