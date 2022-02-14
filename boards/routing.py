from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/boards/(?P<slug>\w+)/$", consumers.BoardConsumer.as_asgi()),
]
