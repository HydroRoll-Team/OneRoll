import ast
import importlib.resources
import unittest
from pathlib import Path

import oneroll
from oneroll import _core


REPOSITORY_ROOT = Path(__file__).parents[1]
CORE_STUB = REPOSITORY_ROOT / "src" / "oneroll" / "_core.pyi"


class TypingContractTests(unittest.TestCase):
    def test_installed_package_declares_pep561_typing_support(self):
        package_files = importlib.resources.files(oneroll)

        self.assertTrue(package_files.joinpath("py.typed").is_file())
        self.assertTrue(package_files.joinpath("_core.pyi").is_file())

    def test_core_stub_matches_runtime_exports_and_methods(self):
        module = ast.parse(CORE_STUB.read_text(encoding="utf-8"))
        stub_functions = {
            node.name for node in module.body if isinstance(node, ast.FunctionDef)
        }
        stub_classes = {
            node.name: {
                item.name
                for item in node.body
                if isinstance(item, ast.FunctionDef) and item.name != "__init__"
            }
            for node in module.body
            if isinstance(node, ast.ClassDef)
        }

        self.assertEqual(
            {name for name in dir(_core) if not name.startswith("_")},
            stub_functions | stub_classes.keys(),
        )
        for class_name, method_names in stub_classes.items():
            runtime_methods = {
                name
                for name in dir(getattr(_core, class_name))
                if not name.startswith("_")
            }
            self.assertEqual(runtime_methods, method_names)


if __name__ == "__main__":
    unittest.main()
