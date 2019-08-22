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
PBS Log Handler: API's to read and process the PBS Accounting logs.

This module can be extended to read and process other types of logs
related to PBS. Ex- Mom/Server logs.

Attributes:
    * DEFAULT_PBS_CONF(str): The default path of the the PBS
                             configuration file - /etc/pbs.conf
    * PBS_JOB_VARS(dict): key is job variable and value is job's usage
                          value.
    * rsrc_types(list): The two types of resources from PBS logs
    are predefined in this list - 'Resource_List' and 'resources_used'.
    The purpose of defining these two in a list so that it can be
    extended to include other PBS resource types('resources_default',
    'resources_available') etc.

Classes:
    * PbsLogHandler: class to provide the API's for reading and
                     processing of logs.
"""

import os
from time import sleep
import logging
from datetime import datetime
from .model.exceptions import PbsConfigNotFoundError, LogLineError

DEFAULT_PBS_CONF = '/etc/pbs.conf'

# List of PBS job variables considered for ingestion as per the job
# state.
PBS_JOB_VARS = {
    'E': ['account', 'accounting_id', 'alt_id', 'ctime',
          'eligible_time', 'end', 'etime', 'exec_host', 'exec_vnode',
          'Exit_status', 'group', 'jobname', 'project', 'qtime',
          'queue', 'run_count', 'session', 'start', 'user'],
    'Q': ['queue'],
    'S': ['accounting_id', 'ctime', 'etime', 'exec_host', 'exec_vnode',
          'group', 'jobname', 'project', 'qtime', 'queue', 'session',
          'start', 'user']
}
RSRC_TYPES = ['Resource_List', 'resources_used']


class PbsLogHandler(object):
    """
    Read and process the PBS accounting logs, return job's attributes.

    By default, start with reading the log file of the current date
    and then wait indeifinitely, processing logs as they arrive,
    and automatically switch to the next file as date changes.
    When called with a day different from today,
    read and process just one log file.

    Attributes:
        pbs_log_path(str) : PBS Accounting log path
        log_file_name(str): starts with current date.
        logger(object) : Application level logging object

    Methods:
        get_accounting_path: returns the accounting files path of PBS
        readline: starts a generator which reads continuously today's
        accounting log file.
        process_log_line: processes the log line to create dicts.

    """

    def __init__(self, day="today"):
        """Find the logfile to be processed, if it exists."""
        self.pbs_log_path = self.get_accounting_path()
        # Set the log file name based on PBS log file name format which is
        # YYYYMMDD
        logform = "%Y%m%d"
        if day == "today":
            day = datetime.now().date().strftime(logform)
            self.run = "today"
        else:
            date = datetime.strptime(day, logform)
            day = date.strftime(logform)
            self.run = "manual"
        self.log_file_name = day
        check = os.path.isfile(os.path.join(self.pbs_log_path, self.log_file_name))
        if not check:
            self.run = "none"
        else:
            self.log = logging.getLogger(__name__)
            self.log.info("Initialising log handler: accounting log file for %s", day)

    def get_first_log(self):
        """
        Find the earliest/oldest log available for processing.

        Args:
            None
        Returns:
            filename
        """
        filename = sorted(os.listdir(self.pbs_log_path))[1]
        return filename

    @staticmethod
    def get_accounting_path():
        """
        Find PBS accounting path under PBS_HOME/server_priv/accounting.

        Get the PBS_HOME path from the default PBS conf file or else
        from the PBS conf file path
        set in the environment variable "PBS_CONF_FILE".

        Append the PBS_HOME path with the accounting path and
        returns the final path.

        Args:
            None

        Returns:
            str - pbs_accounting_path
        """
        try:
            with open(os.getenv('PBS_CONF_FILE', DEFAULT_PBS_CONF)) as pbs_config_file:
                conf_data = pbs_config_file.readlines()
                for each in conf_data:
                    if 'PBS_HOME' in each:
                        return os.path.join(each.rstrip('\n').split('=')[1],
                                            'server_priv', 'accounting')
        except Exception as exc:
            raise PbsConfigNotFoundError(exc)

    def readline(self):
        """
        Read line from file, if there is a line, else wait or exit.

        Check date and, if needed, update the instance variable
        "log_file_name" to read the current date's log file.

        Args:
            None

        Yields:
            str - Log Line string read from PBS Accounting log file

        Example:
            for log_line in read():
                process(line)
        """
        try:
            file_handle = self.open_file()

            while True:
                if self.is_update_needed():
                    if self.run != 'manual':
                        self.update_log_file_name()
                        file_handle.close()
                        file_handle = self.open_file()
                if file_handle is not None:
                    log_line = file_handle.readline()
                else:
                    break
                if not log_line:
                    if self.log_file_name == datetime.now().replace(hour=0,
                                                                    minute=0,
                                                                    second=0).strftime('%Y%m%d'):
                        if self.run == 'manual':
                            self.log.info('Processed past logs, waiting for today''s information')
                            self.run = 'manualwaiting'
                        sleep(0.1)
                        continue
                    else:
                        self.log.info('Finished processing %s log.', self.log_file_name)
                        file_handle.close()
                        break
                elif len(str(log_line).split(";")) == 4 and str(log_line).split(";")[1] == 'L':
                    self.log.info(str(log_line))
                    continue
                yield log_line
        except Exception:
            self.log.exception("Unable to read today's PBS Accounting log file. Please try again "
                               "after the accounting log file exists in the PBS Accounting Path.")
            raise

    def is_update_needed(self):
        """
        Check whether log file name needs to be updated.

        Args:
            None
        Returns:
            bool: True/False
        """
        current_date = datetime.now().replace(hour=0, minute=0, second=0).strftime('%Y%m%d')
        if current_date != self.log_file_name:
            return True
        return False

    def update_log_file_name(self):
        """Update the log file name."""
        current_date = datetime.now().replace(hour=0, minute=0, second=0).strftime('%Y%m%d')
        self.log_file_name = current_date

    def open_file(self):
        """
        Open a file, and return it as a file object.

        If not found, keeps retrying till found - or in manual mode, skips it,
            because it's possible that some dates are missing in the past logs.

        Returns:
            file: Returns a file object.
        """
        file_handle = None
        while file_handle is None:
            try:
                if self.is_update_needed():
                    if self.run != 'manual':
                        self.update_log_file_name()
                file_handle = open(os.path.join(self.pbs_log_path,
                                                self.log_file_name))
            except IOError:
                self.log.error("Accounting log file not found -`%s`!", self.log_file_name)
                if self.run == 'manual':
                    break
                else:
                    self.log.info("Sleeping for 60 secs and trying again")
                    sleep(60)
        return file_handle

    def process_log_line(self, log_msg):
        """
        Process log line to form data structures for post-processing.

        Args:
            log_msg : The log message to be processed

        Returns:
            tuple: A tuple of three dictionaries formed after the
            processing of the log message.

        """
        try:
            log_dict = {}
            log_msg_list = str(log_msg).split(";")
            if len(log_msg_list) != 4:
                raise LogLineError("Log message should have exactly four pieces separated by ';'."
                                   "Exiting for log message: {0}".format(log_msg))
            log_dict['log_date'], log_dict['job_state'], log_dict['job_id'], log_str = log_msg_list
            if log_dict['job_state'] not in PBS_JOB_VARS:
                raise LogLineError('PBS job states: Q, S, E; '
                                   'not {0} as given for job-id {1}.'.format(log_dict['job_state'],
                                                                             log_dict['job_id']))
            rsrc_requested = {}
            rsrc_used = {}
            job_vars_list = [i.split('=', 1) for i in log_str.split(' ')]
            for var in job_vars_list:
                if len(var) > 1:
                    rsrc_type = var[0]
                    val = var[1]
                    try:
                        if rsrc_type in PBS_JOB_VARS[log_dict['job_state']]:
                            log_dict[var[0]] = val.strip()
                        elif 'Resource_List' in rsrc_type:
                            args = var[0].split('.')[1]
                            rsrc_requested[args] = val
                        elif 'resources_used' in rsrc_type:
                            args = var[0].split('.')[1]
                            rsrc_used[args] = val
                        else:
                            self.log.info("Found an undefined PBS Job variable %s with value %s."
                                          "Skipping this variable.", rsrc_type, val)
                    except IndexError:
                        raise LogLineError("Problem with resource %s of value %s in log line %s" %
                                           (rsrc_type, val, log_msg))
                else:
                    raise LogLineError("Problem with 'resource=value' given as %s in log line %s" %
                                       (var, log_msg))
            return log_dict, rsrc_requested, rsrc_used
        except Exception:
            self.log.exception("The message %s is not processed", log_msg)
            raise
