#!/bin/bash
set -Eeuo pipefail

export DJANGO_SETTINGS_MODULE=prod_settings
export PYTHONPATH="/data"

django-admin collectstatic --no-input
django-admin migrate

# populate redis search cache
/app/docker/populate-redis.py

exec gunicorn --bind 0.0.0.0:55523 boogiestats.boogiestats.wsgi --log-level DEBUG --access-logfile /data/access.log --error-logfile /data/error.log --threads "$GUNICORN_THREADS"
