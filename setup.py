"""Set up PBS Gestor package and its modules, for wheel and pex."""
from setuptools import setup

setup(
    name='pbs_gestor',
    version='7.1',
    packages=['pbs_gestor', 'pbs_gestor.model'],
    package_dir={'pbs_gestor': 'pbs_gestor', 'pbs_gestor.model': 'pbs_gestor/model'},
    package_data={'pbs_gestor': ['pbs_gestor_config.json']},
    scripts=['gestor.py'],
    install_requires=[
        'sqlalchemy',
        'psycopg2_binary',
        "importlib_resources ; python_version<'3.7'",
        'appdirs'
    ],
    setup_requires=['wheel'],
    tests_require=[
        'pytest',
    ],
    test_suite='pytest',
    zip_safe=True
)
