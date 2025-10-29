#!/bin/bash
set -o errexit

export DJANGO_SETTINGS_MODULE=citu_campuspass.settings

pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput