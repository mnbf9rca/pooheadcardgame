@ECHO OFF
IF "%SQLALCHEMY_DATABASE_PASSWORD%" == "" GOTO NOCREDS
IF "%SQLALCHEMY_DATABASE_USERNAME%" == "" GOTO NOCREDS
IF "%CONDA_PROMPT_MODIFIER%" == "py3.6" GOTO NOCONDA

:YESCREDS
    set FLASK_APP=application.py 
    set FLASK_ENV=development
    set SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://<creds>@127.0.0.1:5432/poohead"
    flask run --port=8080
GOTO END
:NOCONDA
echo Don't appear to be running in conda environment 'py3.6' - activate conda prompt first
GOTO END
:NOCREDS
@ECHO Either the SQLALCHEMY_DATABASE_PASSWORD or the SQLALCHEMY_DATABASE_USERNAME environment variable was NOT detected.

:END