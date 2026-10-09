"""Gunicorn production entry: ikon_django.wsgi:application."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ikon_django.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
