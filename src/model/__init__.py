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
Hold the basic structure of the Reporting Database tables.

Classes:
    * PbsJob: This holds the structure of table with jobs
      and their attributes: name of the job, running time,
      vnode, user who started it, et cetera.
    * PbsJobArr: This holds the structure of table with job resources:
      assigned to jobs, or used by jobs.
    * PBSLog: This holds the structure of table with log handler records
      of which logs were processed when.
"""
from sqlalchemy import Column, Text, Integer, DateTime, Date, BIGINT, ARRAY, ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship
from .orm_lib import Helpers, BASE

SCHEMA = "cylcreporting"


class PbsJobArr(BASE):
    """Holds table structure: resources assigned to jobs, or used by jobs."""

    # pylint: disable=too-few-public-methods
    __tablename__ = 'pbsjobarr'
    __table_args__ = (UniqueConstraint('ji_pbsjobidx', 'ji_arrresource', 'ji_arrvalue'),
                      {"schema": SCHEMA, "extend_existing": True})
    attributes = ["ji_pbsjobidx", "ji_arrresource", "ji_arrvalue"]
    p_key = ["ji_pbsjobarridx"]

    # Table definition
    ji_pbsjobarridx = Column(Integer, primary_key=True, autoincrement=True)
    ji_pbsjobidx = Column(Integer, ForeignKey(Helpers.schema_ref(SCHEMA, 'pbsjob.ji_pbsjobidx')),
                          nullable=False)
    ji_arrresource = Column(Text)
    ji_arrvalue = Column(Text)

    def __init__(self, **kwargs):
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
    __tablename__ = 'pbslog'
    __table_args__ = {"schema": SCHEMA, "extend_existing": True}
    attributes = ["filename", "start", "end"]
    p_key = ["idx"]

# Table definition
    idx = Column(Integer, primary_key=True, autoincrement=True)
    start = Column(DateTime)
    end = Column(DateTime)
    filename = Column(Date, unique=True)

    def __init__(self, **kwargs):
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
    __tablename__ = 'pbsjob'
    __table_args__ = {"schema": SCHEMA, "extend_existing": True}
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
    pbsjobarr = relationship(PbsJobArr, backref='pbsjob')

    def __init__(self, **kwargs):
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


PBSRAWFLATVIEW = {"__tablename__": "%s.pbsrawflatview" % SCHEMA,
                  "__select__":
                      ("SELECT * FROM"
                       " crosstab('SELECT ji_pbsjobidx,ji_arrresource,ji_arrvalue FROM"
                       " {schema}.{pbsjobarr} WHERE {res}=''u_ncpus'' or {res}=''u_mem'' or"
                       " {res}=''u_vmem'' or {res}=''u_walltime'' or {res}=''u_cput'' or"
                       " {res}=''u_cpupercent'' or {res}=''l_nodect'' or {res}=''l_place''"
                       " order by 1,2;') AS pbsjobarrow(pbsjobidx int,nodect text,place text,"
                       "cpupercent text,cput text,mem text,ncpus text,"
                       "vmem text,walltime text);".format(schema=SCHEMA, pbsjobarr='pbsjobarr',
                                                          res='ji_arrresource'))}


PBSRAWFLATVIEWJOIN = {"__tablename__": "%s.pbsrawflatviewjoin" % SCHEMA,
                      "__select__": ("SELECT {schema}.{pbsrawflatview}.*,{schema}.{pbsjob}.ji_jobid"
                                     " FROM {schema}.{pbsrawflatview} INNER JOIN"
                                     " {schema}.{pbsjob} ON {schema}.{pbsrawflatview}.pbsjobidx"
                                     " = {schema}.{pbsjob}"
                                     ".ji_pbsjobidx;".format(schema=SCHEMA,
                                                             pbsrawflatview='pbsrawflatview',
                                                             pbsjob='pbsjob'))}

TABLES = {
    "pbsjob": PbsJob,
    "pbsjobarr": PbsJobArr,
    "pbslog": PbsLog
}


SQLVIEWS = {
    "pbsrawflatview": PBSRAWFLATVIEW,
    "pbsrawflatviewjoin": PBSRAWFLATVIEWJOIN
}
