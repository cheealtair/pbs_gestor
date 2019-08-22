# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

docs:
	mkdir ../tmp
	mv ../setup.py ../tmp
	mv ../conftest.py ../tmp
	sphinx-apidoc -P -f -o "$(SOURCEDIR)" ../
	@$(SPHINXBUILD) -b pdf "$(SOURCEDIR)" "$(BUILDDIR)"/pdf/
	mv ../tmp/*.py ../
	rmdir ../tmp
	rm ../*.pyc
	rm ../pbs_gestor/*.pyc
	rm ../pbs_gestor/model/*.pyc

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
