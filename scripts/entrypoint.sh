#!/bin/bash

set -e

echo "Waiting for PostgreSQL..."
python scripts/wait-for-db.py

echo "Making migrations..."
python manage.py makemigrations --noinput

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"

