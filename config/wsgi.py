"""
WSGI config for the OneFuture project.

It exposes the WSGI callable as a module-level variable named ``application``
so Gunicorn can import it: ``gunicorn config.wsgi:application``
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
