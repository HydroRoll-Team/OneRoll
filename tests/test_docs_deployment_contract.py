import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WRANGLER_CONFIG = ROOT / "wrangler.docs.jsonc"
PACKAGE_JSON = ROOT / "package.json"


class DocsDeploymentContractTests(unittest.TestCase):
    def test_wrangler_serves_sphinx_output_on_the_documentation_domain(self):
        config = json.loads(WRANGLER_CONFIG.read_text(encoding="utf-8"))

        self.assertEqual(config["name"], "oneroll-docs")
        self.assertEqual(config["assets"]["directory"], "./docs/_build/html")
        self.assertEqual(config["assets"]["not_found_handling"], "none")
        self.assertEqual(
            config["routes"],
            [
                {
                    "pattern": "oneroll.hydroroll.team/*",
                    "zone_name": "hydroroll.team",
                }
            ],
        )

    def test_local_cli_builds_and_deploys_the_same_documentation_target(self):
        package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

        self.assertTrue(package["private"])
        self.assertEqual(package["devDependencies"]["wrangler"], "4.116.0")
        build = package["scripts"]["docs:build"]
        self.assertEqual(
            package["scripts"]["docs:clean"],
            "uv run --frozen sphinx-build -M clean docs/source docs/_build",
        )
        self.assertTrue(build.startswith("npm run docs:clean && "))
        self.assertIn("sphinx-build -W --keep-going", build)
        self.assertIn("-d docs/_build/doctrees", build)
        self.assertIn("-b html docs/source docs/_build/html", build)
        self.assertEqual(
            package["scripts"]["docs:deploy"],
            "npm run docs:build && wrangler deploy --config wrangler.docs.jsonc --strict",
        )


if __name__ == "__main__":
    unittest.main()
