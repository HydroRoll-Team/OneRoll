# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = _build
SPHINXINTL    ?= sphinx-intl 
lang		  ?= zh_CN
ppm			  ?= uv

# Put it first so that "make" without argument is like "make help".
help:
	@$(ppm) run $(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(ppm) run $(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# update translation command
translate:
	@$(ppm) run $(SPHINXINTL) update -p ./build/gettext -l $(lang) $(O)

# build for debug
dev:
	@$(ppm) run sphinx-autobuild source _build/html

rinoh:
	@$(ppm) run $(SPHINXBUILD) -b $(SOURCEDIR) . _build/rinoh $(O)