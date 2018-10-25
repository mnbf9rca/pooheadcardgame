if [[ -z "${SQLALCHEMY_DATABASE_PASSWORD}" ]]; then
    echo "SQLALCHEMY_DATABASE_PASSWORD is not set"
elif [[ -z "${SQLALCHEMY_DATABASE_USERNAME}" ]]; then
    echo "SQLALCHEMY_DATABASE_USERNAME is not set"
else
    source activate py3.6-dev
    export FLASK_APP=application.py 
    export FLASK_ENV=development
    export SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://<creds>@127.0.0.1:5432/poohead"
    flask run --port=8080
fi