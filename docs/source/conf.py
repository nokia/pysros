import os
import sys
sys.path.insert(0, os.path.relpath('../'))


# -- Project information -----------------------------------------------------

project = 'pySROS'
copyright = '2021-2024, Nokia'
author = 'Nokia'

# The full version, including alpha/beta/rc tags
version = '24.7.2'
release = '24.7.2'


# -- General configuration ---------------------------------------------------

extensions = [ 'sphinx.ext.autodoc',
               'sphinx.ext.autosectionlabel',
               'sphinx.ext.autosummary',
               'sphinx.ext.todo',
               'sphinx_rtd_theme'
]

latex_engine = 'pdflatex'
latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    }


templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


autosectionlabel_prefix_document = True

autodoc_member_order = 'bysource'


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = "_static/nokia-logo-blue-2023.png"
html_favicon = '_static/favicon.png'
