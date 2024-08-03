#!/bin/bash
set -Eeuo pipefail

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-boogiestats.boogiestats.settings}
django-admin makemigrations --check
