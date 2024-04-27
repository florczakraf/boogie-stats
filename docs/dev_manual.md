## Environment Setup
You will need Python 3.10+ in order to run BoogieStats because it's built with Django 5.
This project uses [Poetry](https://python-poetry.org/docs/) for managing the environment.
It handles virtual environment creation and package installation.
Follow their docs to learn how to install it.

Once you have Poetry, call:
```
$ poetry install
```
to install all runtime and development requirements, as well as the project itself in [editable mode](https://pip.pypa.io/en/stable/topics/local-project-installs/).

Run this command every time you want to enter the environment:
```
$ poetry shell
```
In contrast to a standard virtualenv, Poetry spawns an augmented subshell instead of sourcing environment to the current one.
In order to leave it, simply call `exit` or press `ctrl-d`.

Let's create a development settings file with the following contents:
```
from boogiestats.boogiestats.settings import *  # noqa

DEBUG = True

# if you want to see song info in the UI, uncomment and properly set BS_CHART_DB_PATH
# BS_CHART_DB_PATH = Path("/path/to/stepmania-chart-db/db")  # see https://github.com/florczakraf/stepmania-chart-db

# you might need to uncomment and modify ALLOWED_HOSTS if you don't run your development server on localhost
# ALLOWED_HOSTS = ["localhost", "127.0.0.1", "any.extra.host.you.need"]

PROMETHEUS_METRICS_EXPORT_PORT_RANGE = None
```
Adjust it as needed.
I usually put it next to the normal settings just for the ease of use (and I will assume that for the next commands):
`boogiestats/boogiestats/settings_dev.py`.

You are now ready to create the database:
```
$ DJANGO_SETTINGS_MODULE=boogiestats.boogiestats.settings_dev django-admin migrate
```
Alternatively, you can `export` the `DJANGO_SETTINGS_MODULE` variable so that it's available for the
new processes created in your current shell session.
That way you won't have to put it before every command.
All examples below will assume that the settings environment variable has already been exported.
Here's how the above command would look like with `DJANGO_SETTINGS_MODULE` exported:
```
$ export DJANGO_SETTINGS_MODULE=boogiestats.boogiestats.settings_dev  # do this only once per shell
$ django-admin migrate  # this command will have access to the DJANGO_SETTINGS_MODULE now
```
It will be created in `boogiestats/db.sqlite3` unless you modify `DATABASES` in your settings.
Migration should also be used when you already have a database but the application's code has changed.
You can safely run it on every repository update because the database tracks the migrations that have already been applied.

At this point we can populate the database with some dummy data.
There's a script available that will add some objects of every type.
It will use song database if you have configured it properly in settings.
The script will only work on a fresh database.
If you already have something there, you can remove the old db and create a new one with the `migrate` command.
```
$ rm boogiestats/db.sqlite3  # optionally remove the old db
$ django-admin migrate  # create fresh db
$ dev/populate-db.py
```

## Running the Application
You are now ready to run django's dev server. It has a built-in option to reload on changes, which works great with
packages that are installed in an editable mode. Please notice that the dev server is not supposed to be used in a production
environment. In order to start the dev server, run:
```
# start a server that listens on http://localhost:8000
$ django-admin runserver 8000

# start a server that listens on all interfaces on port 8000; useful for access over the network, for example from a phone
$ django-admin runserver 0.0.0.0:8000
```

## Tests
BoogieStats uses [pytest](https://docs.pytest.org/) as a test framework. In order to run all tests, run:
```
$ pytest
```
If you need more information about pytest, just consult their docs.

## Coding Standards
BoogieStats enforce multiple standards when it comes to code style and quality. As long as the following commands exit
with 0 status, it's OK. If you need more info, consult the respective tool's docs.
```
$ black .  # reformats python code
$ flake8  # lints the python code
$ djlint --profile django --reformat .  # reformats django templates
$ djlint --profile django --check --lint .  # lints django templates (sometimes you have to do manual fixes because the one above can't fix everything)
$ bandit --configfile bandit.yml -r boogiestats/  # lints the python code for security issues
```

## Modifying Models
Until now, all [models](https://docs.djangoproject.com/en/stable/topics/db/models/) changes could be achieved using normal
django migrations. Unfortunately, some of them, such as the one that introduced collecting score judgment details, could
not be backwards compatible. As a result of that, we have to live with the legacy™.

In order to generate a migration after a change in model, run:
```
$ django-admin makemigrations
```

If you need to modify the migration, for example to add backward compatibility, now is the time for it.
You can check `boogiestats/boogie_api/migrations/0011_player_latest_score.py` for an example of such migration.
When you're happy with your migration, you have to apply it using the `migrate` command (the same
one that we used to create the database before!).
```
$ django-admin migrate
```

## Useful Commands Summary
```
$ poetry install
$ poetry shell
$ pytest
$ black .
$ flake8
$ djlint --profile django --reformat .
$ djlint --profile django --check --lint .
$ bandit --configfile bandit.yml -r boogiestats/
$ DJANGO_SETTINGS_MODULE=boogiestats.boogiestats.settings_dev django-admin runserver 8000
$ DJANGO_SETTINGS_MODULE=boogiestats.boogiestats.settings_dev django-admin migrate
$ DJANGO_SETTINGS_MODULE=boogiestats.boogiestats.settings_dev dev/populate-db.py
$ DJANGO_SETTINGS_MODULE=boogiestats.boogiestats.settings_dev django-admin makemigrations
$ DJANGO_SETTINGS_MODULE=prod.settings django-admin collectstatic
$ DJANGO_SETTINGS_MODULE=prod.settings gunicorn --bind localhost:55523 boogiestats.boogiestats.wsgi --log-level DEBUG --access-logfile access.log --error-logfile error.log --threads 2
```
