"""Optional ASGI entry: ikon_django.asgi:application."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ikon_django.settings')
from django.core.asgi import get_asgi_application
application = get_asgi_application()
