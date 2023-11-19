#!/bin/bash
set -Eeuo pipefail

export DJANGO_SETTINGS_MODULE=prod_settings
export PYTHONPATH="/data"

django-admin collectstatic --no-input
django-admin migrate

# populate redis search cache; delay it in order to lower perceived app startup time
# if redis uses persistent cache, this won't make any difference
/bin/bash -c 'sleep 30; /app/docker/populate-redis.py'&

exec gunicorn \
  --bind 0.0.0.0:55523 \
  --log-level DEBUG \
  --access-logfile /data/access.log \
  --error-logfile /data/error.log \
  --worker-class gthread \
  --threads "$GUNICORN_THREADS" \
  --workers "$GUNICORN_WORKERS" \
  boogiestats.boogiestats.wsgi
