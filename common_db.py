import datetime
import decimal
import logging
import os
import re
import sys
import warnings

import requests
import sqlalchemy
import sqlparse
import termcolor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models





class Common_DB():
    """A singleton Common_DB object which contains a link to a DB connection

        methods:
        .engine() --> return an instance of sqlalchemy.engine.Engine, connected to the database
        .common_Session() --> return a sqlalchemy.orm.session.sessionmaker bound to .engine
        .execute(statement, param1=param1 ...) --> executes a statement without session

    """

    instance = None
    def __new__(cls): # __new__ always a classmethod
        # logging.getLogger(__name__).debug("call to Common_DB()")
        if not Common_DB.instance:
            logging.getLogger(__name__).info("creating new Common_DB.instance")
            Common_DB.instance = Common_DB.__Controller()
        return Common_DB.instance
    def __getattr__(self, name):
        return getattr(self.instance, name)

    class __Controller():
        __common_engine = None
        __common_Sessionmaker = None
        __sqalchemy_database_uri = None
        __secret_key = None
        __logger = None
        def __init__(self):
            """initiates Controller to fetch SQL connection details and instantiate a single engine connection.
            
            properties:
            engine --> return an sqlalchemy.engine.Engine
            sqalchemy_database_uri --> string --> URI of the connected DB
            common_Sessionmaker --> returns a sqlalchemy.orm.session.sessionmaker --> used for session management.
            secret_key --> string --> secret key from metadata store
            """
            self.__logger = logging.getLogger(__name__)
            self.__logger.debug("init Common_DB.__Controller()")
            in_gcp, dburi, sk = self.get_sql_username_password()

            self.__sqalchemy_database_uri = dburi
            self.__secret_key = sk
            # self.__execution_only, self.__common_engine = database_connection.get_database_connection(self.__sqalchemy_database_uri)
            self.__logger.debug("creating common_engine")
            self.__common_engine = create_engine(self.__sqalchemy_database_uri)
            self.__logger.info("Created engine %s", self.__common_engine)

            # Log statements to standard error
            logging.basicConfig(level=logging.DEBUG)
            self.logger = logging.getLogger(__name__ + ".db_engine")
            disabled = self.logger.disabled

            # Test database
            try:
                self.logger.disabled = True
                self.__common_engine.execute("SELECT 1")

            except sqlalchemy.exc.OperationalError as e:
                e = RuntimeError(self.__common_engine._parse(e))
                e.__cause__ = None
                raise e
            else:
                self.logger.disabled = disabled
            
            self.__logger.debug("creating shared sessionmaker")
            self.__common_Sessionmaker = sessionmaker(bind = self.__common_engine)
            self.__logger.info("Created __common_Sessionmaker")

        @property
        def common_Sessionmaker(self):
            """returns a sqlalchemy.orm.session.Session"""
            return self.__common_Sessionmaker
        #common_Session = property(__get_common_Session, doc="returns a sqlalchemy.orm.session.Session")
        
        @property
        def sqalchemy_database_uri(self):
            return self.__sqalchemy_database_uri
        #sqalchemy_database_uri = property(__get_sqalchemy_database_uri)

        @property
        def common_engine(self):
            return self.__common_engine
        #engine = property(__get_common_engine)

        @property
        def secret_key(self):
            return self.__secret_key
        #secret_key = property(__get_secret_key)

        
        def initialise_models(self):
            """Initialises models in the DB using sqlalchemy.schema.MetaData.create_all()"""
            self.__logger.debug("calling models.Base.metata.create_all")
            models.Base.metadata.create_all(self.__common_engine)

        def execute(self, engine_or_session, text, **params):
            """
            Execute a SQL statement.
            modified from https://github.com/cs50/python-cs50
            """
            # Raise exceptions for warnings
            warnings.filterwarnings("error")

            # Prepare, execute statement
            try:

                statement = self.__parse_sql_statement(text = text, **params)

                # Statement for logging
                log = re.sub(r"\n\s*", " ", sqlparse.format(statement, reindent=True))

                # Execute statement
                result = engine_or_session.execute(statement)
                
                # If SELECT (or INSERT with RETURNING), return result set as list of dict objects
                if re.search(r"^\s*SELECT", statement, re.I):

                    # Coerce any decimal.Decimal objects to float objects
                    # https://groups.google.com/d/msg/sqlalchemy/0qXMYJvq8SA/oqtvMD9Uw-kJ
                    rows = [dict(row) for row in result.fetchall()]
                    for row in rows:
                        for column in row:
                            if isinstance(row[column], decimal.Decimal):
                                row[column] = float(row[column])
                    ret = rows

                # If INSERT, return primary key value for a newly inserted row
                elif re.search(r"^\s*INSERT", statement, re.I):
                    if self.__common_engine.url.get_backend_name() in ["postgres", "postgresql"]:
                        result = engine_or_session.execute(sqlalchemy.text("SELECT LASTVAL()"))
                        ret = result.first()[0]
                    else:
                        ret = result.lastrowid
                    if (ret == 0):
                        # no row ID generated
                        # but if there's an exception, that's overridden below
                        # so let's just return True
                        ret = True

                # If DELETE or UPDATE, return number of rows matched
                elif re.search(r"^\s*(?:DELETE|UPDATE)", statement, re.I):
                    ret = result.rowcount

                # If some other statement, return True unless exception
                else:
                    ret = True

            # If constraint violated, return None
            except sqlalchemy.exc.IntegrityError:
                self.logger.debug(termcolor.colored(log, "yellow"))
                return None

            # If user errror
            except sqlalchemy.exc.OperationalError as e:
                self.logger.debug(termcolor.colored(log, "red"))
                e = RuntimeError(self._parse(e))
                e.__cause__ = None
                raise e

            # Return value
            else:
                self.logger.debug(termcolor.colored(log, "green"))
                return ret

        def __parse_sql_statement(self, text, **params):
            """
            Parse and bind paramaters to create a SQL statement.
            adapted from https://github.com/cs50/python-cs50
            """

            class UserDefinedType(sqlalchemy.TypeDecorator):
                """
                Add support for expandable values, a la https://bitbucket.org/zzzeek/sqlalchemy/issues/3953/expanding-parameter.
                """

                impl = sqlalchemy.types.UserDefinedType

                def process_literal_param(self, value, dialect):
                    """Receive a literal parameter value to be rendered inline within a statement."""
                    def process(value):
                        """Render a literal value, escaping as needed."""

                        # bool
                        if isinstance(value, bool):
                            return sqlalchemy.types.Boolean().literal_processor(dialect)(value)

                        # datetime.date
                        elif isinstance(value, datetime.date):
                            return sqlalchemy.types.String().literal_processor(dialect)(value.strftime("%Y-%m-%d"))

                        # datetime.datetime
                        elif isinstance(value, datetime.datetime):
                            return sqlalchemy.types.String().literal_processor(dialect)(value.strftime("%Y-%m-%d %H:%M:%S"))

                        # datetime.time
                        elif isinstance(value, datetime.time):
                            return sqlalchemy.types.String().literal_processor(dialect)(value.strftime("%H:%M:%S"))

                        # float
                        elif isinstance(value, float):
                            return sqlalchemy.types.Float().literal_processor(dialect)(value)

                        # int
                        elif isinstance(value, int):
                            return sqlalchemy.types.Integer().literal_processor(dialect)(value)

                        # long - modified to use int instead of long in py3 so i dont need this
                        # - see https://docs.python.org/3.3/whatsnew/3.0.html#integers
                        # elif sys.version_info.major != 3 and isinstance(value, long):
                        #    return sqlalchemy.types.Integer().literal_processor(dialect)(value)

                        # str
                        elif isinstance(value, str):
                            return sqlalchemy.types.String().literal_processor(dialect)(value)


                        # None
                        elif isinstance(value, sqlalchemy.sql.elements.Null):
                            return sqlalchemy.types.NullType().literal_processor(dialect)(value)

                        # Unsupported value
                        raise RuntimeError("unsupported value")

                    # Process value(s), separating with commas as needed
                    if type(value) is list:
                        return ", ".join([process(v) for v in value])
                    else:
                        return process(value)

            # Allow only one statement at a time
            # SQLite does not support executing many statements
            # https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.execute
            if (len(sqlparse.split(text)) > 1 and
                self.__common_engine.url.get_backend_name() == "sqlite"):
                raise RuntimeError("too many statements at once")

            # Raise exceptions for warnings
            warnings.filterwarnings("error")
            log = re.sub(r"\n\s*", " ", text)

            # Prepare, execute statement
            try:

                # Construct a new TextClause clause
                statement = sqlalchemy.text(text)
                

                # Iterate over parameters
                for key, value in params.items():

                    # Translate None to NULL
                    if value is None:
                        value = sqlalchemy.sql.null()

                    if self.__common_engine.url.get_backend_name() == "sqlite":
                        # for some reason, bool isnt being converted to int
                        if value == True:
                            value = 1
                        elif value == False:
                            value = 0

                    # Bind parameters before statement reaches database, so that bound parameters appear in exceptions
                    # http://docs.sqlalchemy.org/en/latest/core/sqlelement.html#sqlalchemy.sql.expression.text
                    statement = statement.bindparams(sqlalchemy.bindparam(
                        key, value=value, type_=UserDefinedType()))

                # Stringify bound parameters
                # http://docs.sqlalchemy.org/en/latest/faq/sqlexpressions.html#how-do-i-render-sql-expressions-as-strings-possibly-with-bound-parameters-inlined
                statement = str(statement.compile(compile_kwargs={"literal_binds": True}))
                log = re.sub(r"\n\s*", " ", sqlparse.format(statement, reindent=True))
                return statement
            except:
                self.logger.debug(termcolor.colored(log, "red"))
                self.logger.debug(termcolor.colored(sys.exc_info()[0], "red"))
                
                raise
       
        def _parse(self, e):
            """Parses an exception, returns its message.
            from https://github.com/cs50/python-cs50
            """

            # MySQL
            matches = re.search(r"^\(_mysql_exceptions\.OperationalError\) \(\d+, \"(.+)\"\)$", str(e))
            if matches:
                return matches.group(1)

            # PostgreSQL
            matches = re.search(r"^\(psycopg2\.OperationalError\) (.+)$", str(e))
            if matches:
                return matches.group(1)

            # SQLite
            matches = re.search(r"^\(sqlite3\.OperationalError\) (.+)$", str(e))
            if matches:
                return matches.group(1)

            # Default
            return str(e)

        @staticmethod
        def get_sql_username_password():
            """attempts to fetch username and password from google metadata
            server. If it can't do that, it attempts to retrieve them from
            environment variables.
            """
            logger = logging.getLogger(__name__)
            logger.info("fetching sql credentials")
            username, password, secret_key = None, None, None
            metadata_server = "http://metadata.google.internal/computeMetadata/v1/instance/"
            metadata_flavor = {'Metadata-Flavor': 'Google'}
            logger.debug("about to test access to %s", metadata_server)
            try:
                # let's try and fetch metadata from the google cloud internal metadata server
                # if this fails, then we're probably running locally
                gcp = requests.get(metadata_server, headers=metadata_flavor).text
            except:
                logger.info("Not in GCP - could not connect to %s", metadata_server)
                pass
                gcp = None

            try:
                logger.debug("about to try to fetch SQLALCHEMY_DATABASE_URI from os.environ")
                sqlalchemy_database_uri = os.environ['SQLALCHEMY_DATABASE_URI']
            except:
                logger.error("unable to fetch SQLALCHEMY_DATABASE_URI from os.environ")
                raise

            if gcp:
                # we're in google cloud
                # fetch sql username and password from metadata
                metadata_server = "http://metadata/computeMetadata/v1/project/attributes/"
                in_gcp = True
                try:
                    logger.info("Fetching metadata from %s", metadata_server)
                    password = requests.get(
                        metadata_server + 'sqlpassword', headers=metadata_flavor).text
                    username = requests.get(
                        metadata_server + 'sqlusername', headers=metadata_flavor).text
                    secret_key = requests.get(
                        metadata_server + 'session_secret', headers=metadata_flavor).text
                except:
                    pass
            else:
                # not in GCP
                # find credentials from environment variable
                in_gcp = False
                try:
                    logger.info("fetching credentials from os.environ")
                    password = os.environ.get('SQLALCHEMY_DATABASE_PASSWORD')
                    username = os.environ.get('SQLALCHEMY_DATABASE_USERNAME')
                    secret_key = os.environ.get('SECRET_KEY')
                except:
                    pass
            sqlalchemy_database_uri = sqlalchemy_database_uri.replace('<creds>', username + ":" + password)
            logger.info(f"Fetched SQLALCHEMY_DATABASE_PASSWORD: {password is None}, SQLALCHEMY_DATABASE_USERNAME: {username}, SECRET_KEY: {secret_key is None}")
            return in_gcp, sqlalchemy_database_uri, secret_key
