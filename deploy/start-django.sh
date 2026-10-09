#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DJANGO_SECRET_KEY:?Set DJANGO_SECRET_KEY before starting Django in production}"
export DJANGO_SETTINGS_MODULE=ikon_django.settings
exec python -m gunicorn ikon_django.wsgi:application --config deploy/gunicorn.conf.py
