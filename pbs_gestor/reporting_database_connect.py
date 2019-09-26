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
Reporting Database Library: communicate with Reporting Database.

Classes:
    * ReportingDBLib: Derived from ```BaseORMLib``` used to communicate with the Reporting
                      Database (PostgreSQL).
"""
import logging
from .model.orm_lib import BaseORMLib
from .model.exceptions import DatabaseError
from .utils import SCHEMA, TABLES, SQLVIEWS
from .utils import DATA_MAPPER


class ReportingDBLib(BaseORMLib):
    """
    Add to the Reporting DB records of jobs, and of log handler runs.

    Attributes:
        *config (dict) : The configuration object for database communication.

    Methods:
        * _alter_config: Modifies the configuration dictionary.
        * _save_job_info_data_mapper: Modifies the data by applying user defined functions.
        * _insert_pbs_job_data: Inserts data to pbsjob table, as defined in TABLES.
        * _insert_pbs_job_arr_data: Inserts data to pbsjobarr table, as defined in TABLES.
        * _save_job_info: Saves job info to Reporting Database.
        * _save_log_info: Saves log info to Reporting Database,
            inserting it into pbslog table, as defined in TABLES.
        * is_connected_database: Connection to database active or not.
        * write: Method used to write to database.
        * read: Method not yet implemented.
    """

    # Number of retries if connection goes away in the middle
    CONNECTION_RETRIES = 2

    def __init__(self, config):
        """Get logger and initialise database, tables and schema."""
        self.log = logging.getLogger(__name__)
        self.log.info("Initialising Gestor database connection!")
        try:
            super(ReportingDBLib, self).__init__(TABLES, SQLVIEWS, config, schema=SCHEMA,
                                                 connection_retries=self.CONNECTION_RETRIES)
        except Exception as exc:
            self.log.exception(exc)
            raise
        self.log.info("Initialised Gestor database connection!")

    def __enter__(self):
        """Return self."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit and close database connection."""
        if exc_type is not None:
            self.log.warning("%s: %s: %s", exc_type, exc_val, exc_tb)
            self.log.critical("Exiting Gestor daemon!")
        self._close()

    def is_connected_database(self):
        """Check whether connection to database is active or not."""
        return self._is_session_valid()

    def _save_job_info_data_mapper(self, data):
        """
        Modify data by applying functions from ```DATA_MAPPER```.

        Args:
            data (dict): Data to be written to database.

        Returns:
            data (dict/None): Data after applying user defined functions.
                              None, if KeyError exception triggers.
        """
        data = data
        _message = None
        for data_attr, _func in DATA_MAPPER.items():
            try:
                data[data_attr] = _func(data[data_attr]) if data[data_attr] is not None else None
            except KeyError:
                self.log.exception("Attribute not found to apply mapper: %s", data)
                data = None
                raise
        return data

    def _insert_pbs_job_data(self, data, pbs_job):
        """
        Insert job data, except resources, into pbs_job table.

        Args:
            data (dict): Data to be written to database.
            pbs_job(class): Table class of pbs_job table.

        Returns:
            obj(pbs_job instance): pbs_job instance created from data.
        """
        try:
            self.log.info(data)
            obj = {
                "instance": pbs_job(**data),
                "mode": "merge_by_query",
                "class": pbs_job,
                "query_dict": {
                    "ji_jobid": data["ji_jobid"]
                }
            }
        except Exception:
            self.log.exception("Failed to instantiate ```%s.%s``` object. DATA: %s",
                               SCHEMA, pbs_job, data)
            raise
        self._insert([obj])
        return obj["instance"]

    def _insert_pbs_job_arr_data(self, data, ji_arr_resource, ji_arr_value, pbs_job_arr):
        """
        Insert job resources data into pbs_job_arr table.

        Args:
            data (dict): Data to be written to database.
            ji_arr_resource(str): ji_arr_resource value to be written to database.
            ji_arr_value(str): ji_arr_value value to be written to database.
            pbs_job_arr(class): Table class of pbs_job_arr table.

        Returns:
            None
        """
        try:
            obj = {
                "instance": pbs_job_arr(ji_pbsjobidx=data["ji_pbsjobidx"],
                                        ji_arrresource=ji_arr_resource,
                                        ji_arrvalue=ji_arr_value),
                "mode": "merge_by_query",
                "class": TABLES["pbsjobarr"],
                "query_dict": {
                    "ji_pbsjobidx": data["ji_pbsjobidx"],
                    "ji_arrresource": ji_arr_resource,
                    "ji_arrvalue": ji_arr_value
                }
            }
        except Exception:
            self.log.exception("Failed to instantiate ```%s.%s``` object. DATA: %s",
                               SCHEMA,
                               pbs_job_arr,
                               dict(ji_pbsjobidx=data["ji_pbsjobidx"],
                                    ji_arrresource=ji_arr_resource,
                                    ji_arrvalue=ji_arr_value))
            self.log.critical("Failed to save job attribute %s with value %s!", ji_arr_resource,
                              ji_arr_value)
            raise
        self._insert([obj])

    def _save_job_info(self, data):
        """
        Save job info into Reporting Database.

        Args:
            data (dict): Data to be written to database.

        Returns:
            None
        """
        pbs_job = TABLES["pbsjob"]
        pbs_job_arr = TABLES["pbsjobarr"]
        data = self._save_job_info_data_mapper(data)
        if data is not None:
            pbs_job_obj = self._insert_pbs_job_data(data, pbs_job)
            if "resources" in data and isinstance(data["resources"], dict):
                data["ji_pbsjobidx"] = getattr(pbs_job_obj, "ji_pbsjobidx", None)
                for item in data["resources"].items():
                    self._insert_pbs_job_arr_data(data, item[0], item[1], pbs_job_arr)

    def _save_log_info(self, data):
        """
        Save log info into Reporting Database.

        Args:
            data (dict): Data to be written to database.
        Returns:
            None
        """
        pbs_log = TABLES["pbslog"]
        try:
            self.log.info(data)
            obj = {
                "instance": pbs_log(**data),
                "mode": "merge_by_query",
                "class": pbs_log,
                "query_dict": {
                    "filename": data["filename"]
                }
            }
        except Exception:
            self.log.exception("Failed to instantiate ```%s.%s``` object. DATA: %s",
                               SCHEMA, pbs_log, data)
            raise
        self._insert([obj])
        # !!!??? return obj["instance"]

    def write(self, key, data):
        """
        Save data into Reporting Database.

        Args:
            key (str): key is used to map to respective function to write the data.
            data (dict): Data to be written to database.

        Returns:
            None
        Raises:
            ValueError
            KeyError
        """
        if not isinstance(data, dict):
            raise ValueError("Data not a dictionary, type(data): %s" % (str(type(data))),)

        if key == 'job_info':
            try:
                self._save_job_info(data)
                self.log.info("Successfully saved to job database!")
            except (KeyError, ValueError):
                # !!!???More work to be done on exceptions!
                self.log.exception("Saving to job database failed! Data: %s", data)
                raise
            except DatabaseError.ConnectionError:
                self.log.exception("Saving to job database failed!")
                raise
        elif key == 'log_info':
            try:
                self._save_log_info(data)
            except (KeyError, ValueError):
                # !!!???More work to be done on exceptions!
                self.log.exception("Saving to log database failed! Data: %s", data)
                raise
            except DatabaseError.ConnectionError:
                self.log.exception("Saving to log database failed!")
                raise
        else:
            raise KeyError("Key not configured, key: %s" % (key,))

    def lastscan(self):
        """
        Find the last ever scan by log handler, using pbslog table.

        Args:
            None
        Returns:
            filename : the largest/latest date in the pbslog table
        """
        self.log.info("Looking up the last logs ever scanned by log handler...")
        filename = ""
        pbs_log = TABLES["pbslog"]
        try:
            obj = {
                "class": pbs_log,
                "query": "filename"
            }
            res = self.last_table_ordered_column(obj)
            if res is None:
                self.log.info("Empty log table! Have to start from the first log.")
                filename = "firstlog"
                return filename
            else:
                if hasattr(res, 'filename') and hasattr(res, 'start') and hasattr(res, 'end'):
                    filename = res.filename
                    self.log.info("Lastscan was as date %s", filename)
                    return filename
                else:
                    raise AttributeError("Class variable (filename / start / end) not set for %s",
                                         res)

        except Exception:
            self.log.exception("Failed to find the latest ```%s.%s``` object.",
                               SCHEMA, pbs_log)
            raise
        self._insert([obj])
        return filename  # !!!???, obj["instance"]

    def read(self, key):
        """Read is not yet implemented for this module."""
        raise NotImplementedError("Read not implemented for this module!")

    def close(self):
        """Close the session gracefully."""
        self._close()
