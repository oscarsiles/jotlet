import json, logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from .models import Board, Post, Topic


class BoardConsumer(WebsocketConsumer):
    logger = logging.getLogger("mylogger")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board_slug = None
        self.board = None
        self.board_group_name = None
        self.topic_pk = None
        self.post_pk = None

    def connect(self):
        self.board_slug = self.scope['url_route']['kwargs']['slug']
        self.board = Board.objects.get(slug=self.board_slug)
        self.board_group_name = f'board_{self.board_slug}'

        self.accept()

        async_to_sync(self.channel_layer.group_add)(
            self.board_group_name,
            self.channel_name,
        )

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(
            self.board_group_name,
            self.channel_name,
        )

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
