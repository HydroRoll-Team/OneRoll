import importlib.resources
import unittest

import oneroll


class TypingContractTests(unittest.TestCase):
    def test_installed_package_declares_pep561_typing_support(self):
        package_files = importlib.resources.files(oneroll)

        self.assertTrue(package_files.joinpath("py.typed").is_file())
        self.assertTrue(package_files.joinpath("_core.pyi").is_file())


if __name__ == "__main__":
    unittest.main()
