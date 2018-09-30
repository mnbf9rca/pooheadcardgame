import os

import requests


from sql import SQL


def get_sql_username_password():
    """attempts to fetch username and password from google metadata
       server. If it can't do that, it attempts to retrieve them from
       environment variables.
       """

    username, password = None, None
    metadata_server = "http://metadata.google.internal/computeMetadata/v1/instance/"
    metadata_flavor = {'Metadata-Flavor': 'Google'}

    try:
        # let's try and fetch metadata from the google cloud internal metadata server
        # if this fails, then we're running locally
        gcp = requests.get(metadata_server, headers=metadata_flavor).text
    except:
        pass
        gcp = None

    try:
        sqlalchemy_database_uri = os.environ['SQLALCHEMY_DATABASE_URI']
    except:
        raise

    if gcp:
        # we're in google cloud
        # fetch sql username and password from metadata
        metadata_server = "http://metadata/computeMetadata/v1/project/attributes/"
        in_gcp = True
        try:
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
            password = os.environ.get('SQLALCHEMY_DATABASE_PASSWORD')
            username = os.environ.get('SQLALCHEMY_DATABASE_USERNAME')
            secret_key = os.environ.get('SECRET_KEY')
        except:
            pass
    sqlalchemy_database_uri = sqlalchemy_database_uri.replace('<creds>', username + ":" + password)
    return in_gcp, sqlalchemy_database_uri, secret_key


def get_database_connection(connection_string):
    """opens a connection to the database"""
    try:
        db = SQL(connection_string)
    except:
        raise

    return db, db.engine
