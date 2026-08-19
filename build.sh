#!/usr/bin/env bash
# Build script for Render.
# Installs dependencies, runs migrations, collects static files
# and creates the initial superuser when credentials are provided.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [[ -n "$DJANGO_SUPERUSER_USERNAME" ]]; then
  python manage.py createsuperuser --noinput || true
fi