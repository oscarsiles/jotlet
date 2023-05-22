import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from websockets.legacy.protocol import ConnectionClosedError, ConnectionClosedOK

logger = logging.getLogger(__name__)


class BoardConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        self.board_slug = None
        self.board_group_name = None
        super().__init__(*args, **kwargs)

    async def connect(self):
        self.board_slug = self.scope["url_route"]["kwargs"]["slug"]
        self.board_group_name = f"board-{self.board_slug}"

        await cache.aget_or_set(self.board_group_name, 0)
        await cache.aincr(self.board_group_name)
        await cache.atouch(self.board_group_name, 7200)

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
            await cache.atouch(self.board_group_name, 7200)
            if await cache.aget(self.board_group_name) == 0:
                await cache.adelete(self.board_group_name)
            else:
                await self.channel_layer.group_send(
                    self.board_group_name,
                    {
                        "type": "session_disconnected",
                        "sessions": await cache.aget(self.board_group_name),
                    },
                )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(exc)
        finally:
            await self.channel_layer.group_discard(
                self.board_group_name,
                self.channel_name,
            )

    async def session_connected(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def session_disconnected(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def board_preferences_changed(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def board_updated(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def topic_created(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def topic_updated(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def topic_deleted(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def post_created(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def post_updated(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def post_deleted(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass

    async def reaction_updated(self, event):
        try:
            await self.send_json(event)
        except (ConnectionClosedError, ConnectionClosedOK):
            pass
