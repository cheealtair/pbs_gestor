# -*- coding: utf-8 -*-

# Copyright (C) 1994-2019 Altair Engineering, Inc.
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
PBS Gestor: Convert the PBS accounting logs to PostgreSQL database.

This Python script is the PBS Gestor daemon. It reads PBS accounting
log messages, parses them to get the job attributes
and inserts them into the Reporting database (PostgreSQL).

Pre-requisites for running PBS Gestor:
    * Python, version 2.7 or 3.6: https://www.python.org/
    * PBS server accounting logs access
    * PostgreSQL, version 9, such as 9.2 or 9.6: https://www.postgresql.org/

Pre-set-up before running PBS Gestor:
    * PBS is running
    * PostgreSQL has host-based authentication (HBA) configuration
      usually in /var/lib/pgsql/data/pg_hba.conf
    * PostgreSQL server daemon is running
    * Configuration file ~/.config/pbs_gestor/pbs_gestor_config.json
      contains PostgreSQL authentication data, such as:
      hostname, port, username, password, database name

Functions:
    * set_logger: sets the logger for the application.
    * parser: transforms PBS logs into format for PostgreSQL database.
    * event_type: determines type of event in log message
    * date_range: utility function providing range of dates
      between start date and end date,
      including start date and end date
    * main: primary function which run first and calls the other functions as needed.
"""
from __future__ import print_function
import argparse
import logging
import logging.config
import sys
from datetime import datetime, timedelta, date
from sqlalchemy.exc import OperationalError
from pbs_gestor.model.exceptions import ConfigurationError, DatabaseError, LogLineError
from pbs_gestor.pbs_loghandler import PbsLogHandler
from pbs_gestor.utils import LOGGING_CONFIG, GESTOR_CONFIG, GESTOR_FIRST_RUN
from pbs_gestor.reporting_database_connect import ReportingDBLib

LOGFORM = "%Y%m%d"
GESTOR_FIRST_RUN = GESTOR_FIRST_RUN


def set_logger():
    """
    Open and load the logger configuration file, validate and set the logging config.

    Args:
        None
    Returns:
        None
    Raises:
        ConfigurationError
    """
    try:
        logging.config.dictConfig(LOGGING_CONFIG)
    except Exception:
        raise ConfigurationError("Unable to set the Logging configuration. "
                                 "Please try again.")


def log_line_parser(job):
    """
    Parse most of the contents of log line and get the job attributes.

    Args:
        job(tuple): A tuple of three dictionaries formed after the
                    processing of the log message
    Returns:
        attrs(dict): job attributes required in the reporting database.
    """
    attrs = dict()
    attrs["ji_sv_name"] = ""
    log_dict, rsrc_requested, rsrc_used = job
    # Job attributes like Exit status, resources, exec_vnode, exec_host,
    # resource_placement values are extracted.
    for attr in [["ji_exitstat", 'Exit_status'], ["ji_cr_time", 'ctime'],
                 ["ji_quetime", 'qtime'], ["ji_eligible_time", 'etime'],
                 ["ji_start_time", 'start'], ["ji_end_time", 'end'],
                 ["ji_runcount", 'run_count'], ["ji_sessionid", 'session'],
                 ["ji_jobname", 'jobname', ''], ["ji_user", 'user', ''], ["ji_group", 'group', ''],
                 ["ji_project", 'project', ''], ["ji_queue", 'queue', ''],
                 ["ji_jobid", 'job_id', '']]:
        if attr[1] in log_dict and log_dict[attr[1]] is not None:
            attrs[attr[0]] = log_dict[attr[1]]
        else:
            attrs[attr[0]] = (None if len(attr) < 3 else attr[2])
    server_name = attrs["ji_jobid"].split(".")
    attrs["ji_sv_name"] = ("" if len(server_name) < 2 else server_name[1])
    # job resource processing
    attrs["resources"] = {}
    for rsrc_l in rsrc_requested:
        rsrc_name = rsrc_l
        rsrc_value = rsrc_requested[rsrc_l]
        # Note: In the pbs resources table, the resources_requested name
        # is stored with an additional string prefixed to it.
        # Ex - Resources_List.ncpus - l_ncpus, Resources_List.place - l_place.
        # As the resources_requested and resources_used are in the same table.
        # Prefixing with "l_" makes it easier to differentiate.
        if not rsrc_name and not rsrc_value:
            continue
        rsrc_name = "l_" + rsrc_name
        attrs["resources"][rsrc_name] = str(rsrc_value)
    attrs["ji_exechost"] = None
    attrs["ji_execvnode"] = None
    for rsrc_u in rsrc_used:
        rsrc_name = rsrc_u
        rsrc_value = rsrc_used[rsrc_u]
        if not rsrc_name and not rsrc_value:
            continue
        if "exec_host" in rsrc_name:
            attrs["ji_exechost"] = rsrc_value.split('+')
        elif "exec_vnode" in rsrc_name:
            attrs["ji_execvnode"] = rsrc_value.split('+')
        else:
            # Note: In the pbs resources table, the resources_used name is
            # stored with an additional string prefixed to it.
            # Ex - resources_used.ncpus - u_ncpus,
            # resources_used.walltime - u_walltime.
            rsrc_name = "u_" + rsrc_name
            attrs["resources"][rsrc_name] = str(rsrc_value)
    # job placement processing
    # Let's hope it was already done by rsrc_requested, no reason to do it separately, right?
    # No problem if "pack" or something is turned into a str?

    # TO BE MODIFIED
    attrs["ji_priority"] = 1
    attrs["event_type"] = event_type(attrs)
    return attrs


def event_type(parsed_event):
    """
    Determine type of event in log message.

    Args:
        parsed_event(dict): job attributes
    Returns:
        _event_type(text): type of event
    """
    _event_type = "UNKNOWN"
    if "ji_start_time" not in parsed_event or "ji_end_time" not in parsed_event:
        return _event_type

    if parsed_event["ji_start_time"] is not None and parsed_event["ji_end_time"] is not None:
        _event_type = "END"
    elif parsed_event["ji_start_time"] is not None and parsed_event["ji_end_time"] is None:
        _event_type = "START"
    elif parsed_event["ji_start_time"] is None and parsed_event["ji_end_time"] is None:
        _event_type = "QUEUED"

    return _event_type


def date_range(start_date, end_date):
    """
    Create range of dates between start date and end date, inclusively.

    Args:
        start_date: the first date in date range
        end_date: the last date in date range
    Returns:
        date range: list of dates from start date to end date
    """
    for i in range(int((end_date - start_date).days)+1):
        yield start_date + timedelta(days=i)


LOG = logging.getLogger(__name__)  # ???Constant or variable?!!!


def str_to_date(fromday, dath):
    """Parse day given by user and convert it to date."""
    if fromday == 'today':
        fromdate = datetime.now().date()
        fromday = fromdate.strftime(LOGFORM)
    elif fromday == 'lastscan':
        fromdate = dath.lastscan()
        if fromdate == 'firstlog':
            fromdate = datetime.strptime(PbsLogHandler().get_first_log(), LOGFORM).date()
        else:
            fromdate = fromdate+timedelta(days=1)
        fromday = fromdate.strftime(LOGFORM)
    elif fromday == 'firstlog':
        fromdate = datetime.strptime(PbsLogHandler().get_first_log(), LOGFORM).date()
        fromday = fromdate.strftime(LOGFORM)
    else:
        fromdate = datetime.strptime(fromday, LOGFORM).date()
        fromday = fromdate.strftime(LOGFORM)
    return fromdate


def none_to_today(checkdate):
    """
    Check whether date is existing, if not, returns today instead.

    Args:
        checkdate: date to be checked
    Returns:
        checkdate: either given date or current date
    """
    if not checkdate:
        checkdate = datetime.now().date().strftime(LOGFORM)
    return checkdate


def get_input():
    """
    Get arguments provided.

    Args:
        args: list of arguments provided by user to application
    Returns:
        fromdate (str): input argument
        tilldate (str): input argument
    """
    description = ('Process PBS Pro logs across a range of dates. '
                   'After parsing logs in the past (if so requested), '
                   'continues to process today''s logs and run indefinitely.')
    epilog = ("Date range includes the start and end dates. "
              "Possible options for specifying a date: "
              "   'today', 'lastscan', 'firstlog', or else any day given in %s format. "
              "Otherwise, default value of a date is 'today'. "
              "Examples of date in %s format: '%s', '%s'." % (LOGFORM, LOGFORM,
                                                              date(2001, 12, 31)
                                                              .strftime(LOGFORM),
                                                              date(2019, 7, 26).
                                                              strftime(LOGFORM)))
    parser = argparse.ArgumentParser(description=description,
                                     epilog=epilog)
    parser.add_argument('-f', '--fromdate', help='the date from which to begin reading the logs')
    parser.add_argument('-t', '--tilldate', help='the date till which to read the past logs')
    parser.add_argument('-c', '--config', help=('do not establish database connection, '
                                                'just print out location of configuration file'),
                        action='count')
    arguments = parser.parse_args()
    if arguments.config is not None or GESTOR_FIRST_RUN:
        if GESTOR_FIRST_RUN or arguments.config > 0:
            if GESTOR_FIRST_RUN:
                print(("Default settings have been written to the configuration file. "
                       "Please read and edit the settings as appropriate "
                       "for connecting to your PostgreSQL database, "
                       "and then start the program again."))
            sys.exit()
    return arguments.fromdate, arguments.tilldate


def parse_input(fromdate, tilldate, database_handler):
    """
    Parse arguments provided and return a list of log handlers.

    Args:
        fromdate, tilldate: arguments provided by user to application
        database_handler: connection to database, in order to be able to look up
                          the last log file which was ever scanned
    Returns:
        pbs_log_handlers: list of log handlers
    """
    fromdate = str_to_date(none_to_today(fromdate), database_handler)
    tilldate = str_to_date(none_to_today(tilldate), database_handler)
    pbs_log_handlers = []
    print("Will be reading logs from day: %s, till day: %s" % (fromdate, tilldate))
    if fromdate == tilldate:
        pbs_log_handlers.append(PbsLogHandler(fromdate.strftime(LOGFORM)))
    else:
        if fromdate > tilldate:
            fromdate, tilldate = tilldate, fromdate
        for idate in date_range(fromdate, tilldate):
            alog = PbsLogHandler(idate.strftime(LOGFORM))
            if alog.run != 'none':
                pbs_log_handlers.append(alog)
    return pbs_log_handlers


def detect_log_switch(pbs_log_handler, database_handler, logarguments):
    """
    Detect switch of log handler between logs and record it.

    Args:
        pbs_log_handler: Log handler
        logdate: log which is supposed to be in processing
        start: time when processing of log started
    Returns:
        logdate: log which is currently in processing
        start: time now when it started to be processed
        count: lines processed in log file
    """
    count, logdate, start = logarguments
    if pbs_log_handler.run != 'manual':  # If loghandler can auto-jump to the latest log file
        if pbs_log_handler.log_file_name != logdate.strftime(LOGFORM):  # If loghandler has jumped
            # Then we have got to record that one log file has been processed/closed,
            # and another log file is beginning to be processed
            try:
                end = datetime.now().date()
                database_handler.write(key="log_info",
                                       data={'start': start, 'end': end,
                                             'filename': logdate})
                start, count = end, 0
                logdate = datetime.strptime(pbs_log_handler.log_file_name,
                                            LOGFORM).date()
            except Exception:
                LOG.exception("Saving to log database on switch failed.")
                raise
    return logdate, start, count


def main(system_config):
    """
    Read the PBS accounting logs, process and record to SQL database.

    Create PBS Log handler instances to read the PBS accounting logs.
    Each log line is processed to create a tuple of three dictionaries.
    The tuple is sent to log_line_parser() to create dictionary of job attributes.
    The dictionary is written to SQL database.

    Args:
        system_config: configuration object.
    Returns:
         None
    """
    set_logger()
    LOG.info('Starting the PBS Gestor. %s, log file %s', datetime.now(), LOGGING_CONFIG)
    fromday, tillday = get_input()
    try:
        with ReportingDBLib(system_config["database"]) as database_handler:
            if not database_handler.is_connected_database():
                LOG.critical("Unable to connect to database after multiple attempts. %s",
                             system_config["database"])
                sys.exit()
            else:
                LOG.info("Connection to Reporting Database seems to be successful")
        pbs_log_handlers = parse_input(fromday, tillday, database_handler)
        for pbs_log_handler in pbs_log_handlers:
            start, count = datetime.now().date(), 0
            logdate = datetime.strptime(pbs_log_handler.log_file_name, LOGFORM).date()
            print("Processing log %s" % logdate)
            try:
                for log_line in pbs_log_handler.readline():
                    logdate, start, count = detect_log_switch(pbs_log_handler, database_handler,
                                                              [count, logdate, start])
                    try:
                        processed_log = pbs_log_handler.process_log_line(log_line)
                    except LogLineError as exc:
                        LOG.exception("Log file: %s .Log line: %s. %s", logdate, log_line, str(exc))
                        continue
                    parsed_log_message = log_line_parser(processed_log)
                    LOG.info("Successfully parsed for job with ID %s, event %s",
                             parsed_log_message.get("event_type", None),
                             parsed_log_message.get("ji_jobid", None))
                    LOG.info("Attempting to write to database. . .")
                    database_handler.write(key="job_info", data=parsed_log_message)
                    count = count+1
                if count > 0:
                    end = datetime.now().date()
                    database_handler.write(key="log_info", data={'start': start, 'end': end,
                                                                 'filename': logdate})
            except DatabaseError.ConnectionError:
                LOG.critical("Connection to database lost. Exiting Gestor daemon!")
                sys.exit()
            if pbs_log_handler.log_file_name == pbs_log_handlers[-1].log_file_name:
                if pbs_log_handler.log_file_name != datetime.now().date().strftime(LOGFORM):
                    print('Processed past logs till %s, going to today''s logs: %s',
                          pbs_log_handler.log_file_name,
                          datetime.now().date().strftime(LOGFORM))
                    LOG.info('Processed past logs, going to today''s logs: %s',
                             datetime.now().date().strftime(LOGFORM))
                    pbs_log_handlers.append(PbsLogHandler())
        LOG.info("Exiting Gestor daemon!!!")
    except OperationalError:
        LOG.exception("Couldn't connect to database, check contents of Gestor configuration file")
        print("Check database connection settings in configuration file")
        sys.exit()
    except KeyboardInterrupt:
        LOG.exception("Killed by user with keyboard!")
        print("Keyboard Interrupt, application exiting!")
        sys.exit()


if __name__ == '__main__':
    main(GESTOR_CONFIG)
