# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from unittest.mock import MagicMock
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("../.."))


class Mock(MagicMock):

    @classmethod
    def __getattr__(cls, name):
        return MagicMock()


MOCK_MODULES = [
    # 'numpy',
    # 'numpy.core.multiarray',
    # 'matplotlib',
    # 'matplotlib.pyplot',
    # 'matplotlib.colorbar',
    # 'matplotlib.cm',
    # 'matplotlib.artist',
    # 'matplotlib.transforms',
    # 'matplotlib.pylab',
    # 'pylab',
    # 'scipy',
    # 'pandas',
    'PyQt5',
    'PyQt5.Qt',
    'PyQt5.QtGui',
    'PyQt5.QtCore',
    'PyQt5.QtWidgets',
    # 'pyqtgraph',
    # 'pyqtgraph.Qt',
    # 'pyqtgraph.Qt.QtCore',
    # 'pyqtgraph.Qt.QtGui',
    # 'pyqtgraph.Qt.QtGui.QPainterPath',
    # 'pyqtgraph.Qt.QApplication',
    # 'pyqtgraph.QtGui',
    # 'pyqtgraph.functions',
    # 'pyqtgraph.QtCore',
    # 'pyqtgraph.exporters',
    # 'pyqtgraph.colormap',
    # 'pyqtgraph.parametertree',
    # 'pyqtgraph.parametertree.parameterTypes',
    # 'pyqtgraph.ptime',
    # 'sip',
    'sparse',
    'seaborn',
    # 'brian2',
    # 'teili',
    # 'teili.core',
    # 'teili.models',
    # 'teili.models.builder',
    # 'teili.models.parameters',
    # 'teili.models.equations',
    # 'teili.building_blocks',
    # 'teili.stimuli',
    # 'teili.tools',
]

# sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)
# -- Project information -----------------------------------------------------

project = 'teili'
copyright = '2018, Moritz Milde'
author = 'Moritz Milde'

# The short X.Y version
version = '0.2'
# The full version, including alpha/beta/rc tags
release = '1'


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.mathjax',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo']


autodoc_mock_imports = MOCK_MODULES

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# MARKDOWN PARSER
source_parsers = {
    '.md': 'recommonmark.parser.CommonMarkParser',
}
source_suffix = ['.rst', '.md']
#source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ['build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
#
html_sidebars = {
    '**': [
        'relations.html',
        'searchbox.html',
    ]
}


# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'teilidoc'


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'teili.tex', 'teili Documentation',
     'Moritz Milde', 'manual'),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'teili', 'teili Documentation',
     [author], 1)
]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'teili', 'teili Documentation',
     author, 'teili', 'One line description of project.',
     'Miscellaneous'),
]


# -- Extension configuration -------------------------------------------------

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True
