import json
import subprocess
import sys
import unittest


class CliResourcePolicyTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "oneroll", *arguments],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_cli_users_can_inspect_active_limits(self):
        completed = self.run_cli("--show-limits")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        limits = json.loads(completed.stdout)
        self.assertEqual(limits["source_bytes"], 65_536)
        self.assertEqual(limits["batch_samples"], 10_000)

    def test_cli_users_can_lower_a_limit(self):
        completed = self.run_cli("--limit", "source_bytes=2", "1d6")

        self.assertEqual(completed.returncode, 1)
        self.assertIn("[limit.source_bytes]", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
