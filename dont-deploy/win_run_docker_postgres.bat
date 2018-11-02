@ECHO OFF
IF "%SQLALCHEMY_DATABASE_PASSWORD%" == "" GOTO NOCREDS

:YESCREDS
docker create -v /var/lib/postgresql/data --name postgres9.6-data busybox
docker rm local-postgres9.6
docker run --name local-postgres9.6 -p 5432:5432 -e POSTGRES_PASSWORD=%SQLALCHEMY_DATABASE_PASSWORD% -d --volumes-from postgres9.6-data postgres:9.6

GOTO END
:NOCREDS
@ECHO The SQLALCHEMY_DATABASE_PASSWORD environment variable was NOT detected.
:END
