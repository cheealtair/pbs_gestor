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

"""Verify appearance of PBS accounting log messages in Reporting database."""
from time import sleep
import pytest


@pytest.mark.usefixtures("pbs_status", "pbs_gestor_status", "pbs_submit_job", "database_handler")
def test_one_job(pbs_status, pbs_gestor_status, pbs_submit_job, database_handler):
    """
    Submit a PBS Job and read log messages. Verify the PBS Job id matches.

    Args:
        pbs_status: Fixture to test PBS is running
        pbs_gestor_status: Fixture to test PBS Gestor is running
        pbs_submit_job : Fixture to submit a PBS Job
        database_handler : Fixture to access database
    Raises:
        AssertionError
    """
    assert pbs_status is not None
    assert pbs_gestor_status is not None
    handler, tables = database_handler
    obj = {"class": tables["pbsjob"], "query": "substring(ji_jobid from '[0123456789]*')::int"}
    job_id = pbs_submit_job
    res = handler.last_table_ordered_column(obj)
    assert res is not None
    assert hasattr(res, 'ji_jobid')
    if job_id != str(res.ji_jobid):
        sleep(0.1)
        assert res is not None
        assert hasattr(res, 'ji_jobid')
    assert job_id == str(res.ji_jobid)
