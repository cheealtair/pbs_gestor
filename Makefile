test:
	rm -rf .pytest_cache
	rm -rf tests/.pytest_cache
	python -m pytest -p no:cacheprovider tests/
	rm -rf .pytest_cache
	rm -rf tests/.pytest_cache

lint:
	rm -f -r .eggs
	find ./ -name '*.py' | xargs pylint --disable=locally-disabled
	find ./ -name '*.py' | xargs pydocstyle
	find ./ -name '*.py' | xargs pycodestyle --max-line-length=100
	bandit -q ./gestor.py ./pbs_gestor/*.py ./pbs_gestor/model/*.py

run:
	python gestor.py

run2:
	python2 gestor.py

run3:
	python3 gestor.py

build2:
	rm -rf pbs_gestor.egg-info
	python2 -m pip wheel -w . . --isolated
	rm -rf pbs_gestor.egg-info
build3:
	rm -rf pbs_gestor.egg-info
	python3 setup.py bdist_wheel --universal
	python3 -m pip wheel -w . . --isolated
	rm -rf pbs_gestor.egg-info
build34:
	rm -rf pbs_gestor.egg-info
	python3.4 -m pip wheel -w . . --isolated
	rm -rf pbs_gestor.egg-info
build35:
	rm -rf pbs_gestor.egg-info
	python3.5 -m pip wheel -w . . --isolated
	rm -rf pbs_gestor.egg-info
build36:
	rm -rf pbs_gestor.egg-info
	python3.6 -m pip wheel -w . . --isolated
	rm -rf pbs_gestor.egg-info
build37:
	rm -rf pbs_gestor.egg-info
	python3.7 -m pip wheel -w . . --isolated
	rm -rf pbs_gestor.egg-info
buildall:
	rm -rf pbs_gestor.egg-info
	python3 -m pex . -f ../wheelhouse -v -c gestor.py -o pbs_gestor.7.7.pex --disable-cache --no-compile --platform="linux_x86_64-cp-36-cp36m" --platform="linux_x86_64-cp-35-cp35m" --platform="linux_x86_64-cp-34-cp34m" --platform="linux_x86_64-cp-27-cp27mu" --platform="linux_x86_64-cp-37-cp37m"
	rm -rf pbs_gestor.egg-info
buildallwheels:
	rm -rf pbs_gestor.egg-info
	python2.7 -m pip wheel -w . . --isolated
	rm -rf pbs_gestor.egg-info
	python3 setup.py bdist_wheel --universal
	python3 -m pip wheel -w . . --isolated
	rm -rf pbs_gestor.egg-info
	python3.4 -m pip wheel -w . . --isolated
	python3.5 -m pip wheel -w . . --isolated
	python3.6 -m pip wheel -w . . --isolated
	python3.7 -m pip wheel -w . . --isolated
	rm -rf pbs_gestor.egg-info
	python3 -m pex . -f . -v -c gestor.py -o pbs_gestor.pex --disable-cache --no-compile --platform="linux_x86_64-cp-36-cp36m" --platform="linux_x86_64-cp-35-cp35m" --platform="linux_x86_64-cp-34-cp34m" --platform="linux_x86_64-cp-27-cp27mu" --platform="linux_x86_64-cp-37-cp37m"
	rm -rf pbs_gestor.egg-info
clean:
	rm *.pyc
	rm */*.pyc
	rm */*/*.pyc
cleanall:
	rm *.pyc
	rm */*.pyc
	rm */*/*.pyc
	rm -r .eggs
	rm *.whl
