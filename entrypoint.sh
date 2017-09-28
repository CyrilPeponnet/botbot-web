#!/bin/sh

set -e

timer="5"

until pg_isready -h $DB_HOST 2>/dev/null; do
  echo "Postgres is unavailable - sleeping for $timer seconds"
  sleep $timer
done

>&2 echo "Postgres is up - executing command"

manage.py migrate
manage.py collectstatic --noinput
# for dev
#manage.py runserver 0.0.0.0:8080 --settings=botbot.settings
pushd /srv/botbot-web/botbot
export DEBUG=False
export ALLOWED_HOSTS="*"
gunicorn -b 0.0.0.0:8080 wsgi:application
