#!/bin/bash
set -o errexit  # Stop script on first error

# Set Django settings module
export DJANGO_SETTINGS_MODULE=citu_campuspass.citu_campuspass.settings

# Install dependencies
pip install -r ../requirements.txt

# Run Django migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput