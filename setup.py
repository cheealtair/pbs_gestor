"""
Set up PBS Gestor package and its modules, for wheel and pex.

Specifies dependencies and other details of the application,
for building of pbs_gestor.whl (architecture-independent)
and pbs_gestor.pex (multi-platform) with pex.
PEX can run on the platforms for which it was compiled,
see them inside Makefile.
Wheel (pbs_gestor.whl) can be installed on any platform,
as long as pip (or another Python package manager)
pulls in dependencies for the platform (see sqlalchemy,
psycopg2, and others).
"""
from setuptools import setup

setup(
    name='pbs_gestor',
    version='7.8.1',
    packages=['pbs_gestor', 'pbs_gestor.model'],
    package_dir={'pbs_gestor': 'pbs_gestor', 'pbs_gestor.model': 'pbs_gestor/model'},
    package_data={'pbs_gestor': ['pbs_gestor_config.json']},
    scripts=['gestor.py'],
    install_requires=[
        'sqlalchemy',
        'psycopg2_binary',
        'setuptools',
        'appdirs',
    ],
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    setup_requires=['wheel'],
    tests_require=[
        'pytest',
    ],
    python_requires='>=2.7,<3.8',
    test_suite='pytest',
    zip_safe=True
)
