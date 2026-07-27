import unittest

from oneroll.tui import OneRollTUI, RollHistory


class TuiSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_application_composes_the_history_table(self):
        app = OneRollTUI()

        async with app.run_test():
            self.assertEqual(app.query_one(RollHistory).id, "history_table")


if __name__ == "__main__":
    unittest.main()
