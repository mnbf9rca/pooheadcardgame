
if [[ -z "${SQLALCHEMY_DATABASE_PASSWORD}" ]]; then
    echo "SQLALCHEMY_DATABASE_PASSWORD is not set"
else
    docker create -v /var/lib/postgresql/data --name postgres9.6-data busybox

    docker run --name local-postgres-9.6 -p 5432:5432 -e POSTGRES_PASSWORD=$SQLALCHEMY_DATABASE_PASSWORD --volumes-from postgres9.6-data -d postgres:9.6
fi
