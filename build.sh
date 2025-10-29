#!/bin/bash
set -o errexit  # Stop script on first error

# Install dependencies
pip install -r requirements.txt

# Run Django migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput