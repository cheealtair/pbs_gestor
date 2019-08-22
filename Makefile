test:
	python -B -m pytest -p no:cacheprovider
	rm -rf .pytest_cache
	rm -rf tests/.pytest_cache

lint:
	find ./ -name '*.py' | xargs pylint --disable=locally-disabled
	find ./ -name '*.py' | xargs pydocstyle
	find ./ -name '*.py' | xargs pycodestyle --max-line-length=100

run:
	python -B gestor.py

run2:
	python2 -B gestor.py

run3:
	python3 -B gestor.py

build:
	rm -rf pbs_gestor.egg-info
	pip wheel -w . .
	pex . -c gestor.py -o pbs_gestor.pex --disable-cache
	rm -rf pbs_gestor.egg-info
