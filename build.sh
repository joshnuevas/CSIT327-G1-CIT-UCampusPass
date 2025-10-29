#!/bin/bash
set -o errexit  # Stop script on first error

# Install dependencies
pip install -r requirements.txt

# Run Django migrations (inside the citu_campuspass folder)
python citu_campuspass/manage.py migrate --noinput

python citu_campuspass/manage.py collectstatic --noinput