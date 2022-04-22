# Boogie Stats
A pass-through proxy for groovestats.com that records non-ranked song scores.

## Useful commands
```
pip install -e .[dev]
pytest
black .
flake8
DJANGO_SETTINGS_MODULE=boogiestats.boogiestats.settings django-admin runserver 8000
DJANGO_SETTINGS_MODULE=prod.settings gunicorn --bind localhost:55523 boogiestats.boogiestats.wsgi --log-level DEBUG --access-logfile access.log --error-logfile error.log --threads 2
```
