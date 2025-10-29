#!/bin/bash
set -o errexit  # Stop script on first error

# Set Django settings module
export DJANGO_SETTINGS_MODULE=citu_campuspass.citu_campuspass.settings

# Install dependencies
pip install -r ../requirements.txt

# Run migrations
python citu_campuspass/manage.py migrate

# Collect static files
python citu_campuspass/manage.py collectstatic --noinput

# Start Gunicorn
gunicorn citu_campuspass.wsgi:application --bind 0.0.0.0:$PORT