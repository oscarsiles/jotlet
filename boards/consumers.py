from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import caches


class BoardConsumer(AsyncJsonWebsocketConsumer):
    cache = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = caches["locmem"]

    async def connect(self):
        self.board_slug = self.scope["url_route"]["kwargs"]["slug"]
        self.board_group_name = f"board_{self.board_slug}"

        await self.cache.aget_or_set(self.board_group_name, 0)
        await self.cache.aincr(self.board_group_name)
        await self.cache.atouch(self.board_group_name, 86400)

        await self.channel_layer.group_add(
            self.board_group_name,
            self.channel_name,
        )

        await self.channel_layer.group_send(
            self.board_group_name,
            {
                "type": "session_connected",
                "sessions": await self.cache.aget(self.board_group_name),
            },
        )

        await self.accept()

    async def disconnect(self, code):
        try:
            await self.cache.adecr(self.board_group_name)
            await self.cache.atouch(self.board_group_name, 86400)
            if await self.cache.aget(self.board_group_name) == 0:
                await self.cache.adelete(self.board_group_name)
            else:
                await self.channel_layer.group_send(
                    self.board_group_name,
                    {
                        "type": "session_disconnected",
                        "sessions": await self.cache.aget(self.board_group_name),
                    },
                )
        except Exception:
            raise Exception(f"Error while disconnecting socket from board-{self.board_slug}")
        finally:
            await self.channel_layer.group_discard(
                self.board_group_name,
                self.channel_name,
            )

    async def session_connected(self, event):
        await self.send_json(event)

    async def session_disconnected(self, event):
        await self.send_json(event)

    async def topic_created(self, event):
        await self.send_json(event)

    async def topic_updated(self, event):
        await self.send_json(event)

    async def topic_deleted(self, event):
        await self.send_json(event)

    async def post_created(self, event):
        await self.send_json(event)

    async def post_updated(self, event):
        await self.send_json(event)

    async def post_deleted(self, event):
        await self.send_json(event)

    async def reaction_updated(self, event):
        await self.send_json(event)

    async def board_preferences_changed(self, event):
        await self.send_json(event)
