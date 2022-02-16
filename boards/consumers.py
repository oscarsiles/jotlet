import json, logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.core.cache import cache

from .models import Board, Post, Topic


class BoardConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board_slug = None
        self.board_group_name = None

    def connect(self):
        self.board_slug = self.scope["url_route"]["kwargs"]["slug"]
        self.board_group_name = f"board_{self.board_slug}"

        self.accept()

        try:
            cache.incr(self.board_group_name)
        except:
            cache.add(self.board_group_name, 1, 86400)

        async_to_sync(self.channel_layer.group_add)(
            self.board_group_name,
            self.channel_name,
        )

        async_to_sync(self.channel_layer.group_send)(
            self.board_group_name,
            {
                "type": "session_connected",
                "sessions": cache.get(self.board_group_name),
            },
        )

    def disconnect(self, code):
        try:
            cache.decr(self.board_group_name)
            if cache.get(self.board_group_name) == 0:
                cache.delete(self.board_group_name)
        except:
            pass

        async_to_sync(self.channel_layer.group_send)(
            self.board_group_name,
            {
                "type": "session_disconnected",
                "sessions": cache.get(self.board_group_name),
            },
        )

        async_to_sync(self.channel_layer.group_discard)(
            self.board_group_name,
            self.channel_name,
        )

    def session_connected(self, event):
        self.send(text_data=json.dumps(event))

    def session_disconnected(self, event):
        self.send(text_data=json.dumps(event))

    def topic_created(self, event):
        self.send(text_data=json.dumps(event))

    def topic_updated(self, event):
        self.send(text_data=json.dumps(event))

    def topic_deleted(self, event):
        self.send(text_data=json.dumps(event))

    def post_created(self, event):
        self.send(text_data=json.dumps(event))

    def post_updated(self, event):
        self.send(text_data=json.dumps(event))

    def post_deleted(self, event):
        self.send(text_data=json.dumps(event))

    def post_approved(self, event):
        self.send(text_data=json.dumps(event))

    def post_unapproved(self, event):
        self.send(text_data=json.dumps(event))

    def board_preferences_changed(self, event):
        self.send(text_data=json.dumps(event))
