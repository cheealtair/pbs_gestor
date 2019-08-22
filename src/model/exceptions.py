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
Provide custom exceptions for the PBS Gestor modules.

Classes:
    * BaseError: Base class for Exceptions.
    * ConfigurationError: Exception class for Config Errors.
    * PBSConfigNotFoundError: Exception to be raised when PBS's
      config file is not found.
"""


class BaseError(Exception):
    """Base exception class to be inherited by other exceptions."""

    def __init__(self, message):
        """Initialise the exception."""
        Exception.__init__(self)
        self.message = message


class ConfigurationError(BaseError):
    """Exception class for Configuration related issues."""

    pass


class LogLineError(BaseError):
    """Exception class if log line is in wrong format."""

    pass


class PbsConfigNotFoundError(BaseError):
    """Exception class if PBS configuration file is not found."""

    pass


class DatabaseError(BaseError):
    """Exception class for database related operations."""

    class TableCreationError(BaseError):
        """Exception class for database table creation failure."""

        pass

    class ConnectionError(BaseError):
        """Exception class for database connection failure."""

        pass
