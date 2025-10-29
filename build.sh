#!/bin/bash
set -o errexit  # Stop script on first error

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start Gunicorn
gunicorn citu_campuspass.wsgi:application --bind 0.0.0.0:$PORT