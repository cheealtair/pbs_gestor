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
ORMs Library (uses sqlalchemy).

Provide API's to communicate with the Reporting Database(PostgreSQL).

Classes:
    * BaseORMLib: Base class for database-related operations
      using sqlalchemy.
    * Helpers: Helper class for for utility functions.
"""
from datetime import datetime
from sqlalchemy import create_engine, desc
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text
from sqlalchemy.schema import CreateSchema
from psycopg2.sql import SQL, Identifier
from .exceptions import DatabaseError

BASE = declarative_base()


class BaseORMLib(object):
    """
    Deal with database: provide API's for database connection, etc.

    Attributes:
        *tables (dict) : Dictionary holding the table name mapped to their table class.
        *config (dict) : The configuration object for database communication.
        *schema (str) : String object holding the schema name.
        *create (bool) : Flag used to specify whether to attempt to create table and schema.
        *connection_retries(int): Number of times to try connecting to database before
        exception is thrown.

    Methods:
        * _create: Creates schema and table if the don't exist.
        * _create_table: Creates table if they don't exist.
        * _create_schema: Creates schema if they don't exist.
        * _database_engine: Creates a engine from the database configs provided.
        * _set_session: Creates a new session which is used to communicate with the
                        database.
        * _reset_session: Closes the old session and creates a new session.
        * _commit: Commits changes to the database.
        * _rollback: Rolls back the changes in case any exception is encountered.
        * _close: Close the Reporting database connection.
        * _insert: Performs insert within a transaction.
        * _is_session_valid: Checks the session is valid or not.
        * _merge_by_query: Performs merge based on the query dictionary.
    """

    # pylint: disable=too-few-public-methods
    def __init__(self, tables, views, config, schema=None, connection_retries=2):
        """Connect to database, create tables and schema if needed."""
        # pylint: disable=too-many-arguments
        self.__no_of_retries = connection_retries
        self._set_database_engine(config)
        self._set_session()
        self.exschema = schema

        if not self._is_session_valid():
            self._reset_session()

        if not self._create(tables, views, schema, config):
            raise DatabaseError.TableCreationError("Table creation failed. Check logs!")

    def _create(self, tables, views, schema_name, config):
        """
        Create tables and schemas if they don't exist.

        Args:
            tables (dict): Dictionary holding the table name mapped to their table class.
                {
                    <table_name_1>: <table_class instance>,
                    <table_name_2>: <table_class instance>
                }
            schema_name (str/None): String object holding the schema name.

        Returns:
            success (bool): True -> if the table and schema creation was successful or
                                    they already exist.
                            False -> if exception was triggered during table or schema
                                     creation.
        """
        if not isinstance(tables, dict):
            return False  # Raise Exception That Tables Are In A Wrong Format???!!!
        success = True
        if schema_name is not None:
            self._create_schema(schema_name)
        for table_name_instance in tables.items():
            if self._create_table(table_name_instance[1]) is False:
                success = False
                break
        if isinstance(views, dict):
            for view_name_instance in views.items():
                if self._create_view(view_name_instance[1], schema_name, config) is False:
                    success = False
                    break
        return success

    def _create_table(self, thistable):
        """
        Create table if it doesn't exist, from a class instance.

        Args:
            thistable (class): Model class of the table to be created.
        Returns:
            created (bool/Exception): True -> Table created successfully.
                                      False -> Table already exists.
        """
        created = True
        try:
            thistable.__table__.create(self.__engine, checkfirst=True)
            self._commit()
            return created
        except ProgrammingError:
            self._rollback()
            created = None
            raise
        except Exception:
            self._rollback()
            created = False
            raise

    def _create_schema(self, schema_name):
        """
        Create schema if it does not exist.

        Args:
            schema_name (str): Schema to be created.
        """
        try:
            if not self.__engine.dialect.has_schema(self.__engine, schema_name):
                self.__session.execute(CreateSchema(schema_name))
            self._commit()
        except Exception:
            self._rollback()
            self._reset_session()
            raise

    def _create_view(self, view, schema=None, config=None):
        """
        Create view if it doesn't exist.

        Args:
            view (dict): Name and select statement for the view.
        """
        try:
            viewname = view["__tablename__"].split(' ')[0]
            vschema = view["__schema__"].split(' ')[0]
            try:
                pcon = self.__engine.raw_connection().cursor()
                xxx = SQL('NULL from {}.{}').format(Identifier(vschema),
                                                    Identifier(viewname)).as_string(pcon)
                xxx = self.__session.query(xxx).limit(1)
                self.__session.execute(xxx)
                self._commit()
            except ProgrammingError:
                self._rollback()
                try:
                    like = text("information_schema.routines.routine_name like 'crosstab%'")
                    count = self.__session.query('* FROM information_schema.routines')
                    count = count.filter(like).count()
                    if int(count) is 0:
                        self._create_extension(config)
                        self.exschema = 'public'
                    else:
                        like = text("SELECT count(*) FROM information_schema.routines WHERE "
                                    "information_schema.routines.routine_name LIKE 'crosstab%'"
                                    " AND information_schema.routines.routine_schema IN :schemas")
                        like = self.__session.execute(like,
                                                      {"schemas": (schema,
                                                                   'public')}).fetchone()[0]
                        self._commit()
                        if int(like) is 0:
                            like = text("information_schema.routines.routine_name like 'crosstab%'")
                            count = self.__session.query('routine_schema FROM'
                                                         ' information_schema.routines')
                            count = count.filter(like).limit(1)
                            count = self.__session.execute(count).fetchone()[0]
                            self._commit()
                            self.exschema = count
                            like = text("SELECT has_schema_privilege(:exschema, 'USAGE')")
                            like = self.__session.execute(like,
                                                          {"exschema": self.exschema}).fetchone()[0]
                            self._commit()
                            if like is False:
                                self._grant_access(config)
                except:
                    raise
                try:
                    pcon = self.__engine.raw_connection().cursor()
                    xxx = view["__statement__"].as_string(pcon)
                    self.__session.execute(xxx)
                    self._commit()
                except ProgrammingError:
                    self._rollback()
                    try:
                        pcon = self.__engine.raw_connection().cursor()
                        xxx = view["__statement__"].as_string(pcon)
                        yyy = SQL('{}.crosstab').format(Identifier(schema)).as_string(pcon)
                        xxx = xxx.replace(yyy, 'crosstab')
                        self.__session.execute(xxx)
                        self._commit()
                    except ProgrammingError:
                        self._rollback()
                        pcon = self.__engine.raw_connection().cursor()
                        xxx = view["__statement__"].as_string(pcon)
                        yyy = SQL('{}.crosstab').format(Identifier(schema)).as_string(pcon)
                        zzz = SQL('{}.crosstab').format(Identifier(self.exschema)).as_string(pcon)
                        xxx = xxx.replace(yyy, zzz)
                        self.__session.execute(xxx)
                        self._commit()
        except Exception:
            self._rollback()
            self._reset_session()
            raise

    def _grant_access(self, config):
        """
        Grant user access to schema containing tablefunc extension.

        Args:
            config (dict): Database configuration as a dictionary.
        """
        confi = config.copy()
        user = confi["username"]
        superuse = confi.pop("supdatabase"), confi.pop("supusername"), confi.pop("suppassword")
        self.__engine.dispose()
        configdef = confi.copy()
        configdef["username"] = superuse[1]
        configdef["password"] = superuse[2]
        engine = create_engine(URL(**configdef))
        conn = engine.connect()
        conn.execute("commit")
        pcon = engine.raw_connection().cursor()
        conn.execute(SQL("GRANT USAGE "
                         "ON SCHEMA {schema} "
                         "TO {user};").format(schema=Identifier(self.exschema),
                                              user=Identifier(user)).as_string(pcon))
        conn.execute("commit")
        conn.close()
        engine.dispose()
        self._set_database_engine(config)
        self._set_session()

    def _set_database_engine(self, config):
        """
        Create a sqlalchemy engine object.

        Args:
            config (dict): Database configuration as a dictionary.
        """
        confi = config.copy()
        superuse = confi.pop("supdatabase"), confi.pop("supusername"), confi.pop("suppassword")
        self.__engine = create_engine(URL(**confi))
        try:
            try:
                if self.__engine is not None:
                    conn = self.__engine.connect()
                    conn.close()
            except OperationalError:
                configdef = confi.copy()
                configdef["database"] = superuse[0]
                self.__engine.dispose()
                self.__engine = create_engine(URL(**configdef))
                try:
                    conn = self.__engine.connect()
                except OperationalError:
                    self.__engine.dispose()
                    raise
                conn.execute("commit")
                conn.execute("CREATE DATABASE %s;" % config["database"])
                conn.close()
                self.__engine.dispose()
                self.__engine = create_engine(URL(**confi))
        except ProgrammingError:
            raise

    def _create_extension(self, config):
        """Create extension which requires superuser privileges."""
        confi = config.copy()
        superuse = confi.pop("supdatabase"), confi.pop("supusername"), confi.pop("suppassword")
        try:
            if confi["username"] is not superuse[1]:
                self.__engine.dispose()
                configdef = confi.copy()
                configdef["username"] = superuse[1]
                configdef["password"] = superuse[2]
                engine = create_engine(URL(**configdef))
                conn = engine.connect()
                conn.execute("commit")
                conn.execute("CREATE EXTENSION IF NOT EXISTS tablefunc;")
                conn.execute("commit")
                conn.close()
                engine.dispose()
                self._set_database_engine(config)
                self._set_session()
            else:
                conn = self.__engine.connect()
                conn.execute("commit")
                conn.execute("CREATE EXTENSION IF NOT EXISTS tablefunc;")
                conn.execute("commit")
                conn.close()
        except ProgrammingError:
            raise

    def _set_session(self):
        """Create a new sqlalchemy session."""
        self.__session = sessionmaker(bind=self.__engine)()

    def _reset_session(self):
        """
        Close the previous session and start a new one.

        Raises:
            DatabaseError.ConnectionError
        """
        retries = self.__no_of_retries

        while retries > 0:
            if not self._is_session_valid():
                self._close()
                self._set_session()
            else:
                break
            retries -= 1
        else:
            raise DatabaseError.ConnectionError("Connection to database not available!")

    def _is_session_valid(self):
        """Check whether the session is valid or not."""
        _valid = False
        try:
            if self.__session is not None:
                self.__session.query('1').scalar()
                _valid = True
        except Exception:  # !!!!????!!!!????
            self.__session = None
            raise
        return _valid

    def _commit(self):
        """Commit changes to the database."""
        if self.__session is not None:
            self.__session.commit()

    def _rollback(self):
        """Rollback the changes."""
        if self.__session is not None:
            self.__session.rollback()

    def _close(self):
        """Close the existing session."""
        if self.__session is not None:
            self._rollback()
            self.__session.close()

    def _merge(self, _object):
        """Perform sqlalchemy.session.merge()."""
        self.__session.merge(_object)

    def _add(self, _object):
        """Perform sqlalchemy.session.add()."""
        self.__session.add(_object)

    def _merge_by_query(self, obj_dict):
        """Perform merge based on the query dictionary."""
        _res = self.__session.query(obj_dict["class"]).filter_by(**obj_dict["query_dict"]).first()

        if _res is None:
            self._add(obj_dict["instance"])
        else:
            if hasattr(obj_dict["instance"], 'attributes') and \
               hasattr(obj_dict["instance"], 'p_key'):
                for attr in obj_dict["instance"].attributes:
                    if attr not in obj_dict["instance"].p_key:
                        setattr(_res, attr, getattr(obj_dict["instance"], attr))
                # updating the instance
                obj_dict["instance"] = _res
            else:
                raise AttributeError("Class variable (attributes / p_key) not set for %s" %
                                     (obj_dict["instance"],))

    def last_table_ordered_column(self, obj):
        """
        Perform query for the first row of table ordered by column.

        Args:
            obj
        Returns:
            instance
        """
        instance = self.__session.query(obj["class"]).order_by(desc(text(obj["query"]))).first()
        return instance

    def _insert(self, object_arr):
        """
        Perform insert within a transaction.

        Args:
            object_arr (list): List of objects to be inserted.
            [{
                "instance": <object_instance_1>,
                "mode": "<add/merge>"
            },
            {
                "instance": <object_instance_2>,
                "mode": "<add/merge>"
            }].
        Returns:
            None
        """
        _object = None

        try:
            if not self._is_session_valid():
                self._reset_session()
            for obj in object_arr:
                obj.setdefault("mode", "add")

                _object = obj["instance"]
                if obj["mode"] == "merge":
                    self._merge(_object)
                elif obj["mode"] == "add":
                    self._add(_object)
                elif obj["mode"] == "merge_by_query":
                    self._merge_by_query(obj)
                else:
                    raise NotImplementedError("Invalid mode: {mode}".format(mode=obj["mode"]))
            self._commit()
        except DatabaseError.ConnectionError:
            raise
        except Exception:
            self._rollback()
            self._reset_session()
            raise


class Helpers(object):
    """
    Define various utility functions related to database operation.

    Methods:
        * schema_ref: Concatenates schema to table name
    """

    @staticmethod
    def schema_ref(schema, table):
        """
        Concatenate schema name to table name.

        Args:
            schema (str): Schema name.
            table (str): Table name.

        Returns:
            (str): Schema_name.Table_name
        """
        return schema + '.' + table

    @staticmethod
    def timestamp_to_iso_format(timestamp):
        """
        Convert timestamp, if existing, to UTC ISO format.

        Args:
            timestamp
        Returns:
            date&time
        """
        if timestamp is None:
            return None
        return datetime.isoformat(datetime.utcfromtimestamp(int(timestamp)))
