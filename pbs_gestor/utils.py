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
r"""
Hold structure of database, constants and utility functions to be used across PBS Gestor modules.

Include schema, tables and views.

Classes corresponding to tables:
    * PbsJob: This table contains jobs and their attributes:
      name of the job, running time, vnode, user who started it...
      - The table contains 'CONSTRAINT unq_pbsjob UNIQUE (ji_jobid)'
      so that duplicate records are not created for the same job.

    * PbsJobArr: This table contains job resources:
      assigned to jobs (l_* resource names), or used by jobs (u_* resource names).
      One column contains unique job identifier for relationship to PbsJob table,
      another column contains name of resource, and the last column contains value of resource;
      names and values of resources are represented as text.

    * PBSLog: This supplementary table contains log handler records
      of which logs were processed when.

    Upon connecting to the PostgreSQL database

    - for example, with the command
      psql -h hostname -p port -U username  -d databasename
      with default database connection settings it would be
      psql -h localhost -p 5432 -U postgres  -d pbsjoblogsdb
      you would be able to query the contents of the tables inside the database, such as:

    - SELECT * FROM schema.pbsjob;

    OR

    - SELECT * FROM schema.pbsjob WHERE ji_user='username';
      where username is name of a user whose job history you want to look up

    OR

    - SELECT count(*) FROM schema.pbsjob WHERE ji_user='username';
      if you want to count how many jobs the user has run in the past

    OR

    - any other SQL query

    Additionally, there is also a View created, with name specified in the configuration file,
    inside the same schema as tables.

    - PbsFlatView contains a subset of information from PbsJobArr,
      pivoting the table with PostgreSQL's Crosstab function from Tablefunc extension
      so that requested and used resources would be organised into the following columns:
      'mem', 'ncpus', 'walltime', 'cput', 'nodect', 'cpupercent', et cetera
      instead of being contained in a Entity–attribute–value model as in PbsJobArr table.
      See: https://www.postgresql.org/docs/9.2/tablefunc.html#AEN152349
      Resources requested by job are prefixed with l,
      to be differentiated from resources used by job.
      It is also joined with PbsJob table so that Job ID would be available as one of the columns.
      See INNER JOIN on the following documentation page:
      https://www.postgresql.org/docs/9.2/queries-table-expressions.html#QUERIES-JOIN
      The values for the resources, such as ncpus or walltime, are cast to appropriate data types,
      so that arithmetic operations can be performed on them.

    This view can be queried similarly to tables, for example:

    - SELECT * FROM schema.pbsflatviewreqjoin WHERE l_nodect > 1;
      displays list of all jobs which requested/used more than one node.

* For troubleshooting, try to connect to the database with the same settings
    (hostname, port, username, databasename) as are inside pbs_gestor_config.json file.

    - For ease of troubleshooting, application prints out the location from which it is reading
      the configuration file pbs_gestor_config.json . As noted earlier, if you move the file
      to a different location, please create or update the environment variable PBS_GESTOR_CONF
      with the location of pbs_gestor_config.json .

    Check whether schema 'schema' exists by querying list of schemas with '\\dn'
    command inside psql client.

    Check whether tables exist with '\\dt schema.*' command.

    Check whether tablefunc extension is installed with the following command:

    - \\dx+ tablefunc

      If it says 'Did not find any extension named "tablefunc"',
      then Tablefunc extension is not installed and Crosstab function is not available.
      If the Tablefunc extension is installed successfully,
      then there will be list of objects in extension "tablefunc",
      such as connectby, crosstab and normal_rand.

    OR

    - SELECT count(*) FROM information_schema.routines WHERE routine_name LIKE 'crosstab%';

      If it is 0, then Tablefunc extension is not installed and Crosstab function is not available.
      If it is above 0 - for example, 6 - then Crosstab function is available, which is good.

    If Tablefunc extension is installed, then you may also wish to check where it is installed:

    - SELECT routine_schema FROM information_schema.routines WHERE routine_name LIKE 'crosstab%';

    OR

    - SELECT specific_schema FROM information_schema.routines WHERE routine_name LIKE 'crosstab%';

      (these two similar commands usually return the same result)

    to see which schema contains the installed Crosstab function.

    - Application expects this result to be either 'schema' or, failing that,
      something like 'public' so that the function is inside PostgreSQL's search_path.
      See: https://www.postgresql.org/docs/9.2/runtime-config-client.html#GUC-SEARCH-PATH

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

from __future__ import print_function
import os
import json
from datetime import datetime
# try: Dependency problems when trying to package into multi-platform PEX
#     import importlib.resources as pkg_resources
# except ImportError:
#     # Try backported to PY<37 `importlib_resources`.
#     import importlib_resources as pkg_resources
import pkg_resources
import appdirs
# from .model.exceptions import ConfigurationError
# from .model import TABLES, SQLVIEWS
from sqlalchemy import Column, Text, Integer, DateTime, UniqueConstraint, ForeignKey
from sqlalchemy import BIGINT, ARRAY, Date
from sqlalchemy.orm import relationship
from psycopg2.sql import SQL, Identifier
from pbs_gestor.model.orm_lib import BASE
from pbs_gestor.model.orm_lib import Helpers


def get_config():
    """Find and read configuration file and return its contents."""
    try:
        configs_dir_path = appdirs.user_config_dir('pbs_gestor')
        default_pbs_gestor_conf = os.path.join(configs_dir_path, 'pbs_gestor_config.json')
        pbs_gestor_conf = os.getenv('PBS_GESTOR_CONF', default_pbs_gestor_conf)
        if not os.path.isfile(pbs_gestor_conf):
            first_run = True
            create_user_config(pbs_gestor_conf)
        else:
            first_run = False
        with open(pbs_gestor_conf) as pbs_gestor_config:
            print("Loading configuration from file %s." % pbs_gestor_conf)
            data = json.load(pbs_gestor_config)
            database = data["database"]
            if "supdatabase" not in database:
                database["supdatabase"] = "postgres"
            if "supusername" not in database:
                database["supusername"] = "postgres"
            if "suppassword" not in database:
                database["suppassword"] = "postgres"
            return data, first_run
    except Exception:
        raise


def create_user_config(config_file):
    """Create the user's config file."""
    src = pkg_resources.resource_stream(__name__, 'pbs_gestor_config.json')
    try:
        with open(config_file, 'wb+') as dest:
            dest.writelines(src)
    except IOError:
        os.makedirs(os.path.dirname(config_file))
        with open(config_file, 'wb+') as dest:
            dest.writelines(src)


GESTOR_CONFIG, GESTOR_FIRST_RUN = get_config()
LOGGING_CONFIG = GESTOR_CONFIG["logger"]
SCHEMA = GESTOR_CONFIG["schematables"]["schema"]
LOGTABLE = GESTOR_CONFIG["schematables"]["pbsgestorlogtable"]
JOBTABLE = GESTOR_CONFIG["schematables"]["pbsjobtable"]
JOBARRTABLE = GESTOR_CONFIG["schematables"]["pbsjobresourcestable"]
FLATVIEW = GESTOR_CONFIG["schematables"]["pbsjobresourceview"]

DATA_MAPPER = {
    "ji_cr_time": lambda x: datetime.isoformat(datetime.utcfromtimestamp(float(x))),
    "ji_quetime": lambda x: datetime.isoformat(datetime.utcfromtimestamp(float(x))),
    "ji_start_time": lambda x: datetime.isoformat(datetime.utcfromtimestamp(float(x))),
    "ji_end_time": lambda x: datetime.isoformat(datetime.utcfromtimestamp(float(x)))
}


class PbsJobArr(BASE):
    """Holds table structure: resources assigned to jobs, or used by jobs."""

    # pylint: disable=too-few-public-methods
    __tablename__ = JOBARRTABLE  # 'pbsjobarr'  # name
    __table_args__ = (UniqueConstraint('ji_pbsjobidx', 'ji_arrresource', 'ji_arrvalue'),
                      {"schema": SCHEMA, "extend_existing": True})  # schema
    attributes = ["ji_pbsjobidx", "ji_arrresource", "ji_arrvalue"]
    p_key = ["ji_pbsjobarridx"]

    # Table definition
    ji_pbsjobarridx = Column(Integer, primary_key=True, autoincrement=True)
    ji_pbsjobidx = Column(Integer, ForeignKey(Helpers.schema_ref(SCHEMA,  # schema  name
                                                                 '%s.ji_pbsjobidx' % JOBTABLE)),
                          nullable=False)
    ji_arrresource = Column(Text)
    ji_arrvalue = Column(Text)

    def __init__(self, **kwargs):  # , schema=SCHEMA, name='pbsjobarr', pbsjob='pbsjob'
        """Define columns."""
        self.ji_pbsjobidx = kwargs["ji_pbsjobidx"]
        self.ji_arrresource = kwargs["ji_arrresource"]
        self.ji_arrvalue = kwargs["ji_arrvalue"]

    def __str__(self):
        """String representation of the table."""
        _p_key = {
            'ji_pbsjobidx': self.ji_pbsjobidx,
            'arrresource': self.ji_arrresource,
            'arrvalue': self.ji_arrvalue
        }
        return "table :- {table}, p_key :- {attr}".format(table=self.__tablename__, attr=_p_key)


class PbsLog(BASE):
    """
    This class holds the logs of past runs of loghandler.

    These records are utilised to make sure
    that the same logs are not processed over and over again.
    """

    # pylint: disable=too-few-public-methods
    __tablename__ = LOGTABLE  # 'pbslog'  # name
    __table_args__ = {"schema": SCHEMA, "extend_existing": True}  # schema
    attributes = ["filename", "start", "end"]
    p_key = ["idx"]

# Table definition
    idx = Column(Integer, primary_key=True, autoincrement=True)
    start = Column(DateTime)
    end = Column(DateTime)
    filename = Column(Date, unique=True)

    def __init__(self, **kwargs):  # , schema=SCHEMA, name='pbslog'
        """Define columns."""
        self.start = kwargs["start"]
        self.end = kwargs["end"]
        self.filename = kwargs["filename"]

    def __str__(self):
        """String representation of the table."""
        _p_key = {
            'filename': self.filename
        }
        return "table :- {table}, p_key :- {attr}".format(table=self.__tablename__, attr=_p_key)


class PbsJob(BASE):
    """
    Hold the structure of table with jobs.

    Describe when a job was added into a queue,
    started, or finished, and other attributes (except resources).
    """

    # pylint: disable=too-many-instance-attributes,too-few-public-methods
    # Eighteen is reasonable in this case - considering number of columns in the table.
    __tablename__ = JOBTABLE  # 'pbsjob'  # name
    __table_args__ = {"schema": SCHEMA, "extend_existing": True}  # schema
    attributes = ["ji_jobid", "ji_jobname", "ji_user", "ji_group", "ji_project",
                  "ji_sv_name", "ji_queue", "ji_priority", "ji_cr_time", "ji_quetime",
                  "ji_runcount", "ji_eligible_time", "ji_start_time", "ji_end_time",
                  "ji_sessionid", "ji_exitstat", "ji_exechost", "ji_execvnode"]
    p_key = ["ji_pbsjobidx"]

    # Table definition
    ji_pbsjobidx = Column(Integer, primary_key=True, autoincrement=True)
    ji_jobid = Column(Text, nullable=False, unique=True)
    ji_jobname = Column(Text, nullable=False)
    ji_user = Column(Text, nullable=False)
    ji_group = Column(Text, nullable=False)
    ji_project = Column(Text, nullable=False)
    ji_sv_name = Column(Text, nullable=False)
    ji_queue = Column(Text, nullable=False)
    ji_priority = Column(Integer, nullable=False)
    ji_cr_time = Column(DateTime)
    ji_quetime = Column(DateTime)
    ji_runcount = Column(BIGINT)
    ji_eligible_time = Column(BIGINT)
    ji_start_time = Column(DateTime)
    ji_end_time = Column(DateTime)
    ji_sessionid = Column(Integer)
    ji_exitstat = Column(Integer)
    ji_exechost = Column(ARRAY(Text))
    ji_execvnode = Column(ARRAY(Text))
    pbsjobarr = relationship(PbsJobArr, backref=JOBTABLE)  # name

    def __init__(self, **kwargs):  # , schema=SCHEMA, name='pbsjob'
        """Define columns."""
        self.ji_jobid = kwargs["ji_jobid"]
        self.ji_jobname = kwargs["ji_jobname"]
        self.ji_user = kwargs["ji_user"]
        self.ji_group = kwargs["ji_group"]
        self.ji_project = kwargs["ji_project"]
        self.ji_sv_name = kwargs["ji_sv_name"]
        self.ji_queue = kwargs["ji_queue"]
        self.ji_priority = kwargs["ji_priority"]
        self.ji_cr_time = kwargs["ji_cr_time"]
        self.ji_quetime = kwargs["ji_quetime"]
        self.ji_runcount = kwargs["ji_runcount"]
        self.ji_eligible_time = kwargs["ji_eligible_time"]
        self.ji_start_time = kwargs["ji_start_time"]
        self.ji_end_time = kwargs["ji_end_time"]
        self.ji_sessionid = kwargs["ji_sessionid"]
        self.ji_exitstat = kwargs["ji_exitstat"]
        self.ji_exechost = kwargs["ji_exechost"]
        self.ji_execvnode = kwargs["ji_execvnode"]

    def __str__(self):
        """String representation of the table."""
        _p_key = {
            'jobid': self.ji_jobid
        }
        return "table :- {table}, p_key:- {attr}".format(table=self.__tablename__, attr=_p_key)

PBSRAWFLATVIEW = {"__schema__": SCHEMA,
                  "__tablename__": FLATVIEW}  # "pbsflatviewreqjoin"}
PBSRAWFLATVIEW[("__statement"
                "__")] = SQL("CREATE OR REPLACE VIEW {exschema}.{vname} AS "
                             "SELECT {exschema}.{pbsjob}.ji_jobid, "
                             "{tmp}.l_memory,{tmp}.l_ncpus::int,{tmp}.l_nodect::int,{tmp}.l_place,"
                             "{tmp}.l_vmem,{tmp}.l_walltime::interval,"
                             "{tmp}.cpu_percent::int,{tmp}.cpu_time::interval,{tmp}.memory,"
                             "{tmp}.ncpus::int,"
                             "{tmp}.vmem,{tmp}.walltime::interval FROM {exschema}.crosstab"
                             "('select ji_pbsjobidx,{res},ji_arrvalue from {exschema}.{pbsjobarr}"
                             " where {res}=''u_ncpus'' or {res}=''u_mem'' or"
                             " {res}=''u_vmem'' or {res}=''u_walltime'' or "
                             "{res}=''u_cput'' or {res}=''u_cpupercent'' or "
                             "{res}=''l_ncpus'' or {res}=''l_mem'' or {res}=''l_vmem'' or "  # vmem
                             "{res}=''l_walltime'' or "  # walltime
                             "{res}=''l_nodect'' or "
                             "{res}=''l_place'' order by 1,2;', "
                             "'VALUES (''l_mem''), (''l_ncpus''), (''l_nodect''), (''l_place''), "
                             "(''l_vmem''), (''l_walltime''), (''u_cpupercent''), (''u_cput''), "
                             "(''u_mem''), (''u_ncpus''), (''u_vmem''), (''u_walltime'')') "
                             "AS {tmp}(pbsjobidx int,"
                             "l_memory text,l_ncpus text,l_nodect text,l_place text,l_vmem text,"
                             "l_walltime text,"
                             "cpu_percent text,cpu_time text,memory text,ncpus text,"
                             "vmem text,walltime text) INNER JOIN {exschema}.{pbsjob} "
                             "ON {tmp}.pbsjobidx = {exschema}.{pbsjob}.ji_pbsjobidx"
                             ";").format(vname=Identifier(PBSRAWFLATVIEW["__tablename__"]),
                                         pbsjobarr=Identifier(JOBARRTABLE),
                                         pbsjob=Identifier(JOBTABLE),
                                         exschema=Identifier(SCHEMA),
                                         res=Identifier('ji_arrresource'),
                                         tmp=Identifier('pbsjobarrow'))

TABLES = {
    JOBTABLE: PbsJob,
    JOBARRTABLE: PbsJobArr,
    LOGTABLE: PbsLog
}


SQLVIEWS = {
    PBSRAWFLATVIEW["__tablename__"]: PBSRAWFLATVIEW
}
