source activate py36-dev
export FLASK_APP=application.py 
export FLASK_ENV=development
export SQLALCHEMY_DATABASE_URI="mysql+pymysql://<creds>@127.0.0.1:3306/poohead"

export SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://<creds>@127.0.0.1:5432/poohead"
flask run --port=8080