"""
ASGI config for jotlet project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jotlet.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import boards.routing



application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    'websocket': URLRouter(
        boards.routing.websocket_urlpatterns
    ),
})
