#!/bin/bash
set -e

echo "Running Classic Models API migrations..."

MYSQL_HOST=${MYSQL_HOST:-mysql}

echo "Waiting for MySQL to be ready at ${MYSQL_HOST}..."
until nc -z "${MYSQL_HOST}" 3306; do
  echo "MySQL is unavailable - sleeping"
  sleep 2
done

echo "MySQL is up - applying migrations"
python manage.py migrate --noinput

echo "Migrations complete"
