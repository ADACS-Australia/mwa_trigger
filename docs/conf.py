# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from unittest.mock import Mock

import django

sys.path.insert(0, os.path.abspath("."))

# Add path to prop_api
sys.path.insert(0, os.path.abspath('..'))

# sys.path.insert(
#     0, os.path.abspath("/home/batbold/Projects/adacs_project_official/TraceT/prop_api")
# )

print("sys.path:", sys.path)

# Mock Django and other troublesome modules
MOCK_MODULES = [
    'django',
    'django.conf',
    'django.core',
    'django.db',
    'django.utils',
    'django.apps',
    'ninja',
    'ninja.openapi',
    'ninja_jwt',
    'log_filters',
]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)


# -- Project information -----------------------------------------------------

project = "tracet"
copyright = "2023, ADACS"
author = "ADACS"

# The full version, including alpha/beta/rc tags
release = "1"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autosummary",
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.mathjax",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "numpydoc",
    "sphinx_automodapi.automodapi",
    "sphinxcontrib.mermaid",
]
numpydoc_show_class_members = False
autosummary_generate = True
autodoc_member_order = 'bysource'  #

autodoc_mock_imports = MOCK_MODULES  # Mock imports for autodoc to work properly

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
html_logo = "figures/TraceT.png"


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
