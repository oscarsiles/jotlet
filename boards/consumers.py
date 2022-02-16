import json, logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache

from .models import Board, Post, Topic


class BoardConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.board_slug = self.scope["url_route"]["kwargs"]["slug"]
        self.board_group_name = f"board_{self.board_slug}"

        try:
            cache.incr(self.board_group_name)
        except:
            cache.add(self.board_group_name, 1, 86400)

        await self.channel_layer.group_add(
            self.board_group_name,
            self.channel_name,
        )

        await self.channel_layer.group_send(
            self.board_group_name,
            {
                "type": "session_connected",
                "sessions": cache.get(self.board_group_name),
            },
        )
        
        await self.accept()

    async def disconnect(self, code):
        try:
            cache.decr(self.board_group_name)
            if cache.get(self.board_group_name) == 0:
                cache.delete(self.board_group_name)
        except:
            pass

        await self.channel_layer.group_send(
            self.board_group_name,
            {
                "type": "session_disconnected",
                "sessions": cache.get(self.board_group_name),
            },
        )

        await self.channel_layer.group_discard(
            self.board_group_name,
            self.channel_name,
        )

    async def session_connected(self, event):
        await self.send(text_data=json.dumps(event))

    async def session_disconnected(self, event):
        await self.send(text_data=json.dumps(event))

    async def topic_created(self, event):
        await self.send(text_data=json.dumps(event))

    async def topic_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def topic_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    async def post_created(self, event):
        await self.send(text_data=json.dumps(event))

    async def post_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def post_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    async def post_approved(self, event):
        await self.send(text_data=json.dumps(event))

    async def post_unapproved(self, event):
        await self.send(text_data=json.dumps(event))

    async def board_preferences_changed(self, event):
        await self.send(text_data=json.dumps(event))
