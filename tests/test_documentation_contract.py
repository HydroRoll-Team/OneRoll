import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
LANGUAGE_GUIDE = REPOSITORY_ROOT / "docs" / "source" / "language.rst"
GRAMMAR = REPOSITORY_ROOT / "src" / "oneroll" / "grammar.pest"
V2_RFC = REPOSITORY_ROOT / "docs" / "rfcs" / "0001-dice-program-language-v2.rst"
V2_TARGET_GRAMMAR = REPOSITORY_ROOT / "docs" / "rfcs" / "0001-v2-target.pest"
SPHINX_SOURCE = REPOSITORY_ROOT / "docs" / "source"
PUBLIC_TEXT_FILES = (
    REPOSITORY_ROOT / "README.md",
    REPOSITORY_ROOT / "Cargo.toml",
    REPOSITORY_ROOT / "pyproject.toml",
    REPOSITORY_ROOT / "docs" / "source" / "conf.py",
    *(REPOSITORY_ROOT / "docs").rglob("*.rst"),
    *(REPOSITORY_ROOT / "docs").rglob("*.md"),
)


class DocumentationContractTests(unittest.TestCase):
    def test_language_guide_embeds_the_engine_grammar(self):
        guide = LANGUAGE_GUIDE.read_text(encoding="utf-8")
        directive = ".. literalinclude:: ../../src/oneroll/grammar.pest"

        self.assertIn(directive, guide)
        included_path = (
            LANGUAGE_GUIDE.parent / directive.split("::", 1)[1].strip()
        ).resolve()
        self.assertEqual(included_path, GRAMMAR.resolve())
        self.assertTrue(included_path.is_file())
        self.assertIn(":doc:`conformance`", guide)

    def test_v2_rfc_embeds_a_machine_checked_pest_grammar(self):
        rfc = V2_RFC.read_text(encoding="utf-8")
        directive = ".. literalinclude:: ../rfcs/0001-v2-target.pest"

        self.assertIn(directive, rfc)
        included_path = (SPHINX_SOURCE / directive.split("::", 1)[1].strip()).resolve()
        self.assertEqual(included_path, V2_TARGET_GRAMMAR.resolve())
        self.assertTrue(included_path.is_file())

    def test_public_project_references_do_not_use_legacy_names(self):
        forbidden = (
            "hydro_roll",
            "hydro-roll",
            "HydroRoll-Team/HydroRoll",
            "Pyo3 Project Template For HydroRoll",
            "https://github.com/HydroRoll-Team/oneroll",
            '"hydroroll",',
        )

        for path in PUBLIC_TEXT_FILES:
            content = path.read_text(encoding="utf-8")
            for legacy_reference in forbidden:
                with self.subTest(path=path, reference=legacy_reference):
                    self.assertNotIn(legacy_reference, content)

        for manifest in ("Cargo.toml", "pyproject.toml"):
            content = (REPOSITORY_ROOT / manifest).read_text(encoding="utf-8")
            self.assertIn(
                'repository = "https://github.com/HydroRoll-Team/OneRoll"',
                content,
            )


if __name__ == "__main__":
    unittest.main()
