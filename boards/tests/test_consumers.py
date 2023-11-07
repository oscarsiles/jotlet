import re

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache

from boards.routing import websocket_urlpatterns


@pytest.mark.asyncio()
class TestBoardConsumer:
    async def handle_communicator_connect(
        self, application, board_slug, expected_sessions, existing_communicator=None
    ):
        new_communicator = WebsocketCommunicator(application, f"/ws/boards/{board_slug}/")
        await new_communicator.connect()
        message = await self.assert_receive_message(
            board_slug,
            expected_sessions,
            existing_communicator or new_communicator,
        )
        assert "session_connected" in message
        return new_communicator

    async def handle_communicator_disconnect(self, board_slug, expected_sessions, communicator):
        await communicator.disconnect()
        message = await self.assert_receive_message(board_slug, expected_sessions, communicator)
        assert "session_disconnected" in message

    async def assert_receive_message(self, board_slug, expected_sessions, communicator):
        message = await communicator.receive_from()
        assert f'"sessions": {expected_sessions}' in message
        connected = int(re.findall(r"\d+", message)[0])
        assert await cache.aget(f"board-{board_slug}") == connected
        return message

    async def test_session_connect_disconnect_websocket_message(self, board):
        application = URLRouter(websocket_urlpatterns)
        board_group_name = f"board-{board.slug}"
        assert await cache.aget(board_group_name) is None

        communicator1 = await self.handle_communicator_connect(application, board.slug, 1)
        communicator2 = await self.handle_communicator_connect(application, board.slug, 2, communicator1)

        await communicator2.disconnect()
        await self.assert_receive_message(board.slug, 1, communicator1)
        assert await cache.aget(board_group_name) == 1

        await communicator1.disconnect()
        assert await cache.aget(board_group_name) is None
