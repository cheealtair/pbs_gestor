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

"""Define pytest fixtures to be shared across multiple test files."""
from __future__ import print_function
import os
from subprocess import Popen, PIPE
import pytest
from pbs_gestor.pbs_loghandler import DEFAULT_PBS_CONF
from pbs_gestor.reporting_database_connect import ReportingDBLib
from pbs_gestor.utils import TABLES, GESTOR_CONFIG

DEFAULT_PBS_CONF = DEFAULT_PBS_CONF
GESTOR_CONFIG = GESTOR_CONFIG
TABLES = TABLES


def run_cmd(cmd=None, sudo=False, stdin=None, stdout=PIPE, stderr=PIPE):
    """Run Linux command."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    ret = {'out': '', 'err': '', 'rc': 0}
    if sudo:
        cmd = ['sudo', '-H'] + cmd

    popen = Popen(cmd, stdin=stdin, stdout=stdout, stderr=stderr, shell=False)
    (output, errors) = popen.communicate()
    ret['rc'] = popen.returncode

    if output is not None:
        ret['out'] = output.splitlines()
    else:
        ret['out'] = []

    if errors is not None:
        ret['err'] = errors.splitlines()
    else:
        ret['err'] = []
    return ret


def get_pbs_config():
    """Get PBS configuration file data."""
    with open(os.getenv('PBS_CONF_FILE', DEFAULT_PBS_CONF)) as pbs_config_file:
        conf_data = pbs_config_file.readlines()
    return conf_data


@pytest.fixture(scope='module')
def database_handler():
    """Return a database handler to perform database operations."""
    _handler = ReportingDBLib(GESTOR_CONFIG["database"])
    yield _handler, TABLES
    _handler.close()


@pytest.fixture(scope='module')
def event_log():
    """
    Generate example log lines.

    Args:
        None
    Returns:
        None
    """
    return {
        "QueueEventLog": "11/12/2018 13:50:10;Q;0.cylc-vm;queue=workq",

        "StartEventLog": "11/12/2018 13:50:10;S;0.cylc-vm;user=sujata group=sujata "
                         "project=_pbs_project_default jobname=STDIN queue=workq "
                         "ctime=1542010810 qtime=1542010810 etime=1542010810 start=1542010810 "
                         "exec_host=cylc-vm/0 exec_vnode=(cylc-vm:ncpus=1) "
                         "Resource_List.ncpus=1 Resource_List.nodect=1 Resource_List.place=pack"
                         " Resource_List.select=1:ncpus=1 resource_assigned.ncpus=1",

        "EndEventLog": "11/12/2018 13:50:20;E;0.cylc-vm;user=sujata group=sujata "
                       "project=_pbs_project_default jobname=STDIN queue=workq ctime=1542010810 "
                       "qtime=1542010810 etime=1542010810 start=1542010810 exec_host=cylc-vm/0 "
                       "exec_vnode=(cylc-vm:ncpus=1) Resource_List.ncpus=1 Resource_List.nodect=1 "
                       "Resource_List.place=pack Resource_List.select=1:ncpus=1 session=61461 "
                       "end=1542010820 Exit_status=0 resources_used.cpupercent=0 "
                       "resources_used.cput=00:00:00"
                       " resources_used.mem=0kb resources_used.ncpus=1 resources_used.vmem=0kb "
                       "resources_used.walltime=00:00:11 run_count=1"
    }


@pytest.fixture(scope='module')
def pbs_gestor_status():
    """Return PBS Gestor status."""
    process_name = b"pbs_gestor"
    cmd = ["ps", "-Af"]
    ret = run_cmd(cmd=cmd)
    retl = list(ret["out"])

    for each in list(retl):
        if process_name not in each:
            retl.remove(each)
        else:
            print(each)
            break
    assert len(retl) > 0
    print(retl[0])
    return retl[0]


@pytest.fixture(scope='module')
def pbs_status():
    """Return PBS server status."""
    pbs_path = ""
    conf_data = get_pbs_config()
    for each in conf_data:
        if 'PBS_EXEC' in each:
            pbs_path = os.path.join(each.rstrip('\n').split('=')[1])
    exec_cmd = os.path.join(pbs_path, 'bin', 'qstat')

    cmd = [exec_cmd, "-Bf"]
    ret = run_cmd(cmd=cmd)
    assert ret["rc"] == 0
    print(ret["out"][0])
    return ret["out"][0]


@pytest.fixture(scope='function')
def pbs_submit_job():
    """
    Submit a PBS Job and yield the job ID.

    Args:
        None
    Returns:
        Job ID
    """
    pbs_path = ""
    conf_data = get_pbs_config()
    for each in conf_data:
        if 'PBS_EXEC' in each:
            pbs_path = os.path.join(each.rstrip('\n').split('=')[1])
    exec_cmd = os.path.join(pbs_path, 'bin', 'qsub')

    cmd = [exec_cmd, '--', '/bin/sleep', '100']
    ret = run_cmd(cmd=cmd)
    assert ret["rc"] == 0
    print(ret["out"][0])
    return ret["out"][0]

#    exec_cmd = os.path.join(pbs_path, 'bin', 'qdel')
#    cmd = [exec_cmd, ret["out"][0]]
#    run_cmd(cmd=cmd)
