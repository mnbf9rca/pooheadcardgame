from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database_connection
class Common_DB():
    class __Controller():
        __common_engine = None
        __common_Session = None
        __execution_only = None
        __sqalchemy_database_uri = None
        __secret_key = None
        def __init__(self):
            """initiates Controller to fetch SQL connection details and instantiate a single engine connection.
            
            properties:
            sqalchemy_database_uri --> string --> URI of the connected DB
            execution_only --> SQL object --> wrapper using SQL class to provide swift execution-only SQL
            common_Session --> sqlalchemy.orm.session.Session --> used for session management.
            secret_key --> string --> secret key for flask sessions
            """
            in_gcp, dburi, sk = database_connection.get_sql_username_password()
            self.__sqalchemy_database_uri = dburi
            self.__secret_key = sk
            self.__execution_only, self.__common_engine = database_connection.get_database_connection(self.__sqalchemy_database_uri)
            self.__common_Session = sessionmaker(bind = self.__common_engine)
   
        def __get_execution_only(self):
            return self.__execution_only
        execution_only = property(__get_execution_only)
    
        def __get_common_Session(self):
            return self.__common_Session
        common_Session = property(__get_common_Session)
        
        
        def __get_sqalchemy_database_uri(self):
            return self.__sqalchemy_database_uri
        sqalchemy_database_uri = property(__get_sqalchemy_database_uri)

        
        def __get_secret_key(self):
            return self.__secret_key
        secret_key = property(__get_secret_key)

    instance = None
    def __new__(cls): # __new__ always a classmethod
        if not Common_DB.instance:
            Common_DB.instance = Common_DB.__Controller()
        return Common_DB.instance
    def __getattr__(self, name):
        return getattr(self.instance, name)

    