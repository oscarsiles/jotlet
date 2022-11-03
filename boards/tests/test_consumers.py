import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache

from boards.routing import websocket_urlpatterns


@pytest.mark.asyncio
class TestBoardConsumer:
    async def test_session_connect_disconnect_websocket_message(self, board):
        application = URLRouter(websocket_urlpatterns)
        board_group_name = f"board-{board.slug}"
        assert await cache.aget(board_group_name) is None

        communicator1 = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        await communicator1.connect()
        message = await communicator1.receive_from()
        assert "session_connected" in message
        assert '"sessions": 1' in message
        assert await cache.aget(board_group_name) == 1

        communicator2 = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        await communicator2.connect()
        message = await communicator1.receive_from()
        assert "session_connected" in message
        assert '"sessions": 2' in message
        assert await cache.aget(board_group_name) == 2

        await communicator2.disconnect()
        message = await communicator1.receive_from()
        assert "session_disconnected" in message
        assert '"sessions": 1' in message
        assert await cache.aget(board_group_name) == 1

        await communicator1.disconnect()
        assert await cache.aget(board_group_name) is None
