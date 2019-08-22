# -*- coding: utf-8 -*-

# Copyright (C) 1994-2018 Altair Engineering, Inc.
# For more information, contact Altair at www.altair.com.
#
# Commercial License Information:
#
# For a copy of the commercial license terms and conditions,
# go to: (http://www.pbspro.com/UserArea/agreement.html)
# or contact the Altair Legal Department.
#
# Use of Altair’s trademarks, including but not limited to "PBS™",
# "PBS Professional®", and "PBS Pro™" and Altair’s logos is subject
# to Altair's trademark licensing policies.

"""
Constants or utility functions to be used across modules of PBS Gestor.

Attributes:
    * CONFIGS_DIR_PATH: The path where all the configuration files
    required by PBS Gestor reside. The current codebase works with
    having the configs directory and having the json files like
    pbs_gestor_config.json
    * GESTOR_CONFIG: Dictionary of pbs gestor related config
    * DEFAULT_PBS_GESTOR_CONF: The default path of the the PBS Gestor
    configuration file - ~/.config/pbs_gestor/psb_gestor_config.json
    * LOGGING_CONFIG : The logger configuration for PBS Gestor
"""

import os
import json
from datetime import datetime
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources
import appdirs
from .model.exceptions import ConfigurationError
from .model import TABLES, SCHEMA, SQLVIEWS


def get_config():
    """Find and read configuration file and return its contents."""
    try:
        configs_dir_path = appdirs.user_config_dir('pbs_gestor')
        default_pbs_gestor_conf = os.path.join(configs_dir_path, 'pbs_gestor_config.json')
        pbs_gestor_conf = os.getenv('PBS_GESTOR_CONF', default_pbs_gestor_conf)
        if not os.path.isfile(pbs_gestor_conf):
            create_user_config(pbs_gestor_conf)
        with open(pbs_gestor_conf) as pbs_gestor_config:
            data = json.load(pbs_gestor_config)
            return data
    except Exception as exc:
        raise ConfigurationError(exc)


def create_user_config(config_file):
    """Create the user's config file."""
    source = pkg_resources.open_text('pbs_gestor', 'pbs_gestor_config.json')
    try:
        with open(config_file, 'w+') as dest:
            dest.writelines(source)
    except IOError:
        os.makedirs(os.path.dirname(config_file))
        with open(config_file, 'w+') as dest:
            dest.writelines(source)


GESTOR_CONFIG = get_config()

LOGGING_CONFIG = GESTOR_CONFIG["logger"]

TABLES = TABLES
SCHEMA = SCHEMA
SQLVIEWS = SQLVIEWS

DATA_MAPPER = {
    "ji_cr_time": lambda x: datetime.isoformat(datetime.utcfromtimestamp(float(x))),
    "ji_quetime": lambda x: datetime.isoformat(datetime.utcfromtimestamp(float(x))),
    "ji_start_time": lambda x: datetime.isoformat(datetime.utcfromtimestamp(float(x))),
    "ji_end_time": lambda x: datetime.isoformat(datetime.utcfromtimestamp(float(x)))
}
