#!/bin/bash

set -e

echo "Waiting for PostgreSQL..."
python scripts/wait-for-db.py

echo "Making migrations..."
python manage.py makemigrations --noinput

echo "Running migrations..."
python manage.py migrate --noinput

echo "Cleaning old static files..."
rm -rf /app/staticfiles/*

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting server..."
if [ "$#" -eq 0 ]; then
    PORT=${PORT:-8000}
    WORKERS=${WEB_CONCURRENCY:-4}
    exec gunicorn --bind "0.0.0.0:${PORT}" --workers "${WORKERS}" --timeout 120 --access-logfile - --error-logfile - xcellar.wsgi:application
else
    exec "$@"
fi

