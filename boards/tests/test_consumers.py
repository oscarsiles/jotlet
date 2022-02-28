from django.core.cache import caches
from django.test import TestCase

from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from boards.models import Board
from boards.routing import websocket_urlpatterns


class BoardConsumerTest(TestCase):
    cache = caches["mem-cache"]

    @classmethod
    def setUpTestData(cls):
        Board.objects.create(title="Test Board", description="Test Board Description")

    async def test_session_connect_disconnect_websocket_message(self):
        application = URLRouter(websocket_urlpatterns)
        board = await database_sync_to_async(Board.objects.get)(title="Test Board")
        board_group_name = f"board_{board.slug}"
        self.assertEqual(self.cache.get(board_group_name), None)

        communicator1 = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, subprotocol = await communicator1.connect()
        self.assertTrue(connected, "Could not connect")
        await database_sync_to_async(self.client.login)(username="testuser1", password="1X<ISRUkw+tuK")
        message = await communicator1.receive_from()
        self.assertIn("session_connected", message)
        self.assertIn('"sessions": 1', message)
        self.assertEqual(self.cache.get(board_group_name), 1)

        communicator2 = WebsocketCommunicator(application, f"/ws/boards/{board.slug}/")
        connected, subprotocol = await communicator2.connect()
        message = await communicator1.receive_from()
        self.assertIn("session_connected", message)
        self.assertIn('"sessions": 2', message)
        self.assertEqual(self.cache.get(board_group_name), 2)

        await communicator2.disconnect()
        message = await communicator1.receive_from()
        self.assertIn("session_disconnected", message)
        self.assertIn('"sessions": 1', message)
        self.assertEqual(self.cache.get(board_group_name), 1)

        await communicator1.disconnect()
        self.assertEqual(self.cache.get(board_group_name), None)
