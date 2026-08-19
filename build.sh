#!/usr/bin/env bash
# Build script for Render.
# Installs dependencies, runs migrations and collects static files.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py migrate --noinput
python manage.py collectstatic --noinput