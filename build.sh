#!/bin/bash
set -o errexit

export DJANGO_SETTINGS_MODULE=citu_campuspass.settings

pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn citu_campuspass.wsgi:application --bind 0.0.0.0:$PORT
