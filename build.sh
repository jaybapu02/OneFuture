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
  python manage.py shell -c "
import os
from django.contrib.auth.models import User
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
if username and password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser {username} created.')
else:
    print('Superuser already exists or credentials missing; skipping.')
"
fi