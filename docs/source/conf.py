# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def setup(app):
    app.add_config_value("releaselevel", "", "env")


CARGO_TOML = Path(__file__).resolve().parents[2] / "Cargo.toml"
with CARGO_TOML.open("rb") as cargo_file:
    PACKAGE = tomllib.load(cargo_file)["package"]

PROJECT_VERSION = PACKAGE["version"]
AUTHORS = ", ".join(PACKAGE["authors"])

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "OneRoll"
release = PROJECT_VERSION
copyright = "2023-PRESENT, HydroRoll-Team."
author = AUTHORS

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.extlinks",
    "sphinx.ext.graphviz",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.imgmath",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.httpdomain",
    "sphinx.ext.ifconfig",
    "myst_parser",
    "sphinx_click",
]

autosectionlabel_prefix_document = True

doctest_global_setup = """
import oneroll
"""
todo_include_todos = False
todo_emit_warnings = False
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
extlinks = {
    "issue": ("https://github.com/HydroRoll-Team/OneRoll/issues/%s", "[issue %s]"),
}
source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}
rst_prolog = """
.. ifconfig:: releaselevel in ('alpha', 'beta', 'rc')

   .. warning::
   
        This stuff is only included in the built docs for unstable versions.

"""
rst_epilog = """
.. |psf| replace:: Python Software Foundation
"""
numfig = True
pygments_style = "rrt"
math_number_all = True
html_split_index = True
# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = []
html_extra_path = ["_headers"]

html_css_files = [
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/fontawesome.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/brands.min.css",
]

html_copy_source = True
html_show_sourcelink = True

html_theme_options = {
    "source_repository": "https://github.com/HydroRoll-Team/OneRoll/",
    "source_branch": "main",
    "source_directory": "docs/source/",
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/HydroRoll-Team/OneRoll/",
            "html": "",
            "class": "fa-brands fa-github",
        },
        {
            "name": "Pypi",
            "url": "https://pypi.org/project/oneroll/",
            "html": "",
            "class": "fa-brands fa-python",
        },
    ],
}

latex_documents = [
    ("index", "oneroll.tex", "OneRoll Documentation", AUTHORS, "manual"),
]
