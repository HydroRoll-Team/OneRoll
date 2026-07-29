import unittest

import oneroll
from oneroll.tui import OneRollTUI, RollHistory


class TuiSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_application_composes_the_history_table(self):
        app = OneRollTUI()

        async with app.run_test():
            self.assertEqual(app.query_one(RollHistory).id, "history_table")

    async def test_application_uses_the_configured_policy(self):
        policy = oneroll.ResourcePolicy().with_limit("source_bytes", 2)
        app = OneRollTUI(policy)

        async with app.run_test():
            with self.assertRaisesRegex(ValueError, r"\[limit\.source_bytes\]"):
                app.roller.roll("1d6")


if __name__ == "__main__":
    unittest.main()
