import unittest

import oneroll


class CheckedArithmeticTests(unittest.TestCase):
    def test_python_roll_accepts_a_value_above_i32_max(self):
        result = oneroll.roll("2147483648")

        self.assertEqual(result["total"], 2_147_483_648)

    def test_python_roll_accepts_both_i64_boundaries(self):
        self.assertEqual(oneroll.roll("9223372036854775807")["total"], 2**63 - 1)
        self.assertEqual(oneroll.roll("-9223372036854775808")["total"], -(2**63))

    def test_addition_overflow_is_a_stable_value_error(self):
        with self.assertRaisesRegex(ValueError, r"\[arithmetic\.overflow\]"):
            oneroll.roll("9223372036854775807 + 1")

    def test_subtraction_overflow_is_a_stable_value_error(self):
        with self.assertRaisesRegex(ValueError, r"\[arithmetic\.overflow\]"):
            oneroll.roll("-9223372036854775808 - 1")

    def test_multiplication_overflow_is_a_stable_value_error(self):
        with self.assertRaisesRegex(ValueError, r"\[arithmetic\.overflow\]"):
            oneroll.roll("3037000500 * 3037000500")

    def test_division_by_zero_has_a_stable_error_code(self):
        with self.assertRaisesRegex(ValueError, r"\[arithmetic\.divide_by_zero\]"):
            oneroll.roll("1 / 0")

    def test_division_overflow_is_a_stable_value_error(self):
        with self.assertRaisesRegex(ValueError, r"\[arithmetic\.overflow\]"):
            oneroll.roll("-9223372036854775808 / -1")

    def test_negative_exponent_has_a_stable_error_code(self):
        with self.assertRaisesRegex(ValueError, r"\[arithmetic\.invalid_exponent\]"):
            oneroll.roll("2 ^ -1")

    def test_exponent_above_u32_max_has_a_stable_error_code(self):
        with self.assertRaisesRegex(ValueError, r"\[arithmetic\.invalid_exponent\]"):
            oneroll.roll("2 ^ 4294967296")

    def test_exponentiation_overflow_is_a_stable_value_error(self):
        with self.assertRaisesRegex(ValueError, r"\[arithmetic\.overflow\]"):
            oneroll.roll("2 ^ 63")

    def test_zero_to_the_zero_power_is_one(self):
        self.assertEqual(oneroll.roll("0 ^ 0")["total"], 1)

    def test_division_truncates_toward_zero_for_every_sign_pair(self):
        cases = {
            "5 / 2": 2,
            "-5 / 2": -2,
            "5 / -2": -2,
            "-5 / -2": 2,
        }

        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(oneroll.roll(expression)["total"], expected)


if __name__ == "__main__":
    unittest.main()
