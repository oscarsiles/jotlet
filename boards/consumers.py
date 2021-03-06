import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache


class BoardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.board_slug = self.scope["url_route"]["kwargs"]["slug"]
        self.board_group_name = f"board_{self.board_slug}"

        await cache.aget_or_set(self.board_group_name, 0)
        await cache.aincr(self.board_group_name)
        await cache.atouch(self.board_group_name, 86400)

        await self.channel_layer.group_add(
            self.board_group_name,
            self.channel_name,
        )

        await self.channel_layer.group_send(
            self.board_group_name,
            {
                "type": "session_connected",
                "sessions": await cache.aget(self.board_group_name),
            },
        )

        await self.accept()

    async def disconnect(self, code):
        try:
            await cache.adecr(self.board_group_name)
            await cache.atouch(self.board_group_name, 86400)
            if await cache.aget(self.board_group_name) == 0:
                await cache.adelete(self.board_group_name)
        except Exception:
            raise Exception(f"Error while disconnecting socket from board-{self.board_slug}")

        await self.channel_layer.group_send(
            self.board_group_name,
            {
                "type": "session_disconnected",
                "sessions": await cache.aget(self.board_group_name),
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

    async def reaction_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def board_preferences_changed(self, event):
        await self.send(text_data=json.dumps(event))
